# Redmine seed script — run inside the redmine container via:
#   docker compose exec -T redmine bundle exec rails runner /seed/seed_redmine.rb
#
# Uses Redmine's own models (not the REST API) so we can create the things the
# REST API can't: custom-field definitions, trackers, enumerations. It writes
# the admin API key to /seed/out/redmine_key.txt for the test harness to read.
#
# Designed to be idempotent-ish: it bails early if the test project already
# exists, so re-running against a live stack is safe.
#
# NOTE: model API is Redmine-version-sensitive. Pinned to redmine:5.1.

require 'json'

PROJECT_ID = 'testproj'
# The /seed mount is read-only; we print machine-readable lines (REDMINE_API_KEY,
# SEED_OK <json>) and the host-side harness captures stdout and persists them.

# --- Instance-level settings ---------------------------------------------
Setting.rest_api_enabled = '1'
Setting.host_name = 'localhost:3000'
Setting.protocol = 'http'
Setting.text_formatting = 'textile'

# The official redmine image does NOT load default data (roles, trackers, issue
# statuses, priorities, activities) — load it so the fixture has something to
# build on.
if Redmine::DefaultData::Loader.no_data?
  Redmine::DefaultData::Loader.load('en')
  puts 'Loaded Redmine default data.'
end

# Push Redmine issue ids clear of GitLab's own 1,2,3.. iid sequence, so that
# "gitlab iid == redmine id" is a MEANINGFUL assertion and not a coincidence of
# both counters starting at 1 (matters especially on a fresh DB).
ActiveRecord::Base.connection.execute(
  "SELECT setval('issues_id_seq', GREATEST(1000, (SELECT COALESCE(MAX(id), 0) FROM issues)))")

admin = User.find_by_login('admin')
admin.update_columns(must_change_passwd: false) if admin.respond_to?(:must_change_passwd)
api_key = admin.api_key # generates + persists a token if none exists
puts "REDMINE_API_KEY=#{api_key}"

# Reseed cleanly: destroy a prior fixture project (cascades to issues/wiki/etc).
existing = Project.find_by_identifier(PROJECT_ID)
existing.destroy if existing

# --- Users ---------------------------------------------------------------
# alice + bob have matching GitLab users (see setup_gitlab.rb) -> mapped.
# charlie has NO GitLab counterpart -> exercises the unmapped/fallback path
# (attributed to the migrator/root account).
def make_user(login, first, last)
  u = User.find_by_login(login)
  return u if u
  u = User.new(login: login, firstname: first, lastname: last,
               mail: "#{login}@example.com", language: 'en')
  u.password = 'Passw0rd!e2e'
  u.password_confirmation = 'Passw0rd!e2e'
  u.admin = false
  u.status = User::STATUS_ACTIVE
  u.save!
  u
end

alice   = make_user('alice',   'Alice',   'Mapped')
bob     = make_user('bob',     'Bob',     'Mapped')
charlie = make_user('charlie', 'Charlie', 'Unmapped')

# --- Custom field (exercised via --custom-fields Customer) ----------------
# Must be linked to trackers, otherwise Redmine silently ignores the value.
cf = IssueCustomField.find_by_name('Customer') ||
     IssueCustomField.create!(name: 'Customer', field_format: 'string',
                              is_for_all: true, is_filter: true)
cf.trackers = Tracker.all
cf.save!

# --- Project -------------------------------------------------------------
project = Project.new(name: 'Test Project', identifier: PROJECT_ID,
                      description: 'E2E migration fixture')
project.enabled_module_names = %w[issue_tracking wiki time_tracking]
project.trackers = Tracker.all
project.save!
project.members << Member.new(user: alice, roles: [Role.givable.first])
project.members << Member.new(user: bob,   roles: [Role.givable.first])
cf.projects << project unless cf.is_for_all
project.issue_custom_fields << cf

# --- Categories ----------------------------------------------------------
cat_backend = IssueCategory.create!(project: project, name: 'Backend', assigned_to: bob)

# --- Versions -> become GitLab milestones (roadmap command) --------------
v_open = Version.create!(project: project, name: 'v1.0', status: 'open',
                         description: 'First public version',
                         due_date: Date.today + 30)
v_closed = Version.create!(project: project, name: 'v0.9', status: 'closed',
                           description: 'Pre-release')

# --- Enumerations (ship with Redmine defaults) ---------------------------
tracker_feature = Tracker.find_by_name('Feature') || Tracker.first
tracker_bug     = Tracker.find_by_name('Bug') || Tracker.first
status_new      = IssueStatus.find_by_name('New') || IssueStatus.first
status_closed   = IssueStatus.where(is_closed: true).first || IssueStatus.last
prio_high       = IssuePriority.find_by_name('High') || IssuePriority.active.first
prio_normal     = IssuePriority.find_by_name('Normal') || IssuePriority.active.first
activity        = TimeEntryActivity.first

# --- Issue A: the "rich" open issue --------------------------------------
issue_a = Issue.new(
  project: project, tracker: tracker_feature, author: alice, assigned_to: bob,
  subject: 'Support SSL',
  description: "h1. Needs SSL\n\nWe *must* support @https@. See \"docs\":http://example.com.",
  status: status_new, priority: prio_high, category: cat_backend,
  fixed_version: v_open, due_date: Date.today + 14, estimated_hours: 4.0)
issue_a.custom_field_values = { cf.id => 'ACME Corp' }
issue_a.save!

# Reload before each journal: Redmine uses optimistic locking, so a fresh
# object each time avoids ActiveRecord::StaleObjectError.
def add_note(issue_id, user, notes = nil)
  i = Issue.find(issue_id)
  i.init_journal(user, notes)
  yield i if block_given?
  i.save!
end

# note by a mapped user
add_note(issue_a.id, alice, 'Started looking into this. Textile *bold* works.')
# note by the UNMAPPED user (charlie) -> should attribute to migrator/root
add_note(issue_a.id, charlie, 'I have context on this too.')
# status-only change with an EMPTY note -> must be dropped by the converter
add_note(issue_a.id, bob) { |i| i.priority = prio_normal }

# attachment
att_path = '/seed/sample.txt'
if File.exist?(att_path)
  Attachment.create!(container: issue_a, author: alice,
                     file: File.open(att_path), filename: 'sample.txt',
                     description: 'a sample attachment')
end

# time spent -> spent_hours
TimeEntry.create!(project: project, issue: issue_a, user: alice, hours: 2.5,
                  activity: activity, spent_on: Date.today, comments: 'work')

# --- Issue B: authored by the UNMAPPED user (closed further below) --------
issue_b = Issue.new(
  project: project, tracker: tracker_bug, author: charlie,
  subject: 'Crash on startup', description: 'Boom.',
  status: status_new, priority: prio_normal)
issue_b.save!

# --- Issue C: child of B, related to A -----------------------------------
# Created while B is still OPEN — Redmine forbids attaching an open subtask to
# a closed parent.
issue_c = Issue.new(
  project: project, tracker: tracker_bug, author: bob,
  subject: 'Follow-up cleanup', description: 'Tidy up after the crash fix.',
  status: status_new, priority: prio_normal)
issue_c.parent_issue_id = issue_b.id
issue_c.save!
IssueRelation.create!(issue_from: issue_c, issue_to: issue_a,
                      relation_type: IssueRelation::TYPE_RELATES)

# Now close B.
add_note(issue_b.id, alice, 'Fixed in the latest build.') { |i| i.status = status_closed }
issue_b.reload
issue_b.update_columns(closed_on: Time.now) if issue_b.closed_on.nil?

# --- Wiki with history (pages command) -----------------------------------
wiki = project.wiki || Wiki.create!(project: project, start_page: 'Wiki')
project.reload
home = WikiPage.new(wiki: wiki, title: 'Wiki')
home.content = WikiContent.new(text: "h1. Home\n\nVersion one.", author: alice)
home.save!
home.content.text = "h1. Home\n\nVersion two, see [[Details]]."
home.content.author = bob
home.content.comments = 'link to details'
home.content.save!

details = WikiPage.new(wiki: wiki, title: 'Details')
details.content = WikiContent.new(
  text: "h1. Details\n\nSome *details* with a @code@ span.", author: alice)
details.save!

# --- Summary emitted on stdout for the harness to capture -----------------
summary = {
  'project_identifier' => PROJECT_ID,
  'issues' => {
    'A' => issue_a.id, 'B' => issue_b.id, 'C' => issue_c.id
  },
  'versions' => { 'open' => v_open.name, 'closed' => v_closed.name },
  'users' => { 'mapped' => %w[alice bob], 'unmapped' => %w[charlie] },
}
puts "SEED_OK #{summary.to_json}"
