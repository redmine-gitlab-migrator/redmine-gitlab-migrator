# GitLab setup script — run inside the gitlab container via:
#   docker compose exec -T gitlab gitlab-rails runner /seed/setup_gitlab.rb
#
# Creates:
#   - matching users (alice, bob) so the login->username mapping resolves
#     (charlie is intentionally absent -> exercises the migrator fallback)
#   - a root personal access token with api+sudo scope (needed for --sudo
#     impersonation, which requires an admin token)
#   - two EMPTY target projects under the root namespace, one per migration
#     mode: root/target-iid and root/target-keepid
#
# Writes the token to /seed/out/gitlab_token.txt for the harness.
#
# NOTE: model/service API is GitLab-version-sensitive. Pinned to 16.11 CE.

# The /seed mount is read-only; we print GITLAB_OK token=<value> on stdout and
# the host-side harness captures it.
root = User.find_by_username('root')

# --- Matching users ------------------------------------------------------
# Use Users::CreateService so the personal namespace is built for us — a bare
# User.new(...).save! fails with "Namespace can't be blank" on modern GitLab.
#
# GitLab 19.x (Organizations/Cells) additionally requires organization_id, or
# creation fails with "Namespace organization can't be blank". Pass it when the
# feature is present so this stays compatible with 18.x too.
org_id =
  if defined?(Organizations::Organization) &&
     Organizations::Organization.respond_to?(:default_organization)
    Organizations::Organization.default_organization&.id
  end

%w[alice bob].each do |uname|
  next if User.find_by_username(uname)
  params = {
    username: uname, email: "#{uname}@example.com", name: uname.capitalize,
    password: 'Passw0rd!e2e12', password_confirmation: 'Passw0rd!e2e12',
    skip_confirmation: true
  }
  params[:organization_id] = org_id if org_id
  result = Users::CreateService.new(root, params).execute
  # .execute returns a ServiceResponse and does NOT raise on failure — surface it.
  if result.respond_to?(:success?) && !result.success?
    raise "Failed to create user #{uname}: #{result.message}"
  end
end

# --- Root personal access token (api + sudo) -----------------------------
TOKEN_VALUE = 'e2e-root-token-000000000000'
existing = root.personal_access_tokens.active.find_by(name: 'e2e')
unless existing
  t = root.personal_access_tokens.create!(
    scopes: %w[api sudo], name: 'e2e', expires_at: 365.days.from_now)
  t.set_token(TOKEN_VALUE)
  t.save!
end

# --- Empty target projects (one per migration mode) ----------------------
# The mapped users MUST be members of the target project, at OWNER level:
#  - membership: the migrator impersonates the author via the SUDO header, and
#    GitLab returns "404 Project Not Found" if that user can't see the private
#    project;
#  - OWNER specifically: setting a custom `iid` at creation time (what
#    `--keep-id` does) is only honoured for admins / project owners, so a plain
#    Developer's SUDO'd create silently gets an auto-assigned iid instead.
members = %w[alice bob].map { |n| User.find_by_username(n) }
%w[target-iid target-keepid].each do |path|
  project = Project.find_by_full_path("root/#{path}")
  project ||= Projects::CreateService.new(
    root,
    name: path, path: path,
    namespace_id: root.namespace.id,
    visibility_level: Gitlab::VisibilityLevel::PRIVATE,
    initialize_with_readme: false
  ).execute
  members.each do |u|
    if project.member?(u)
      project.member(u).update!(access_level: Gitlab::Access::OWNER)
    else
      project.add_member(u, Gitlab::Access::OWNER)
    end
  end
end

puts "GITLAB_OK token=#{TOKEN_VALUE}"
