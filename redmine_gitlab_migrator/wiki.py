from git import Repo, Actor

import pypandoc
import logging
import re
import unicodedata

log = logging.getLogger(__name__)

class TextileConverter():
    def __init__(self):
        # make sure we use at least version 17 of pandoc
        # TODO: fix this test, it will not work properly for version 1.2 or 1.100
        version = pypandoc.get_pandoc_version()
        if (version < "1.17"):
            log.error('You need at least pandoc 1.17.0, download from http://pandoc.org/installing.html')
            exit(1)

        # precompile regular expressions
        self.regexWikiLinkWithText = re.compile(r'\\\[\\\[\s*([^\]]*?)\s*\|\s*([^\]]*?)\s*\\\]\\\]')
        self.regexWikiLinkWithoutText = re.compile(r'\\\[\\\[\s*([^\]]*?)\s*\\\]\\\]')
        self.regexTipMacro = re.compile(r'\{\{tip\((.*?)\)\}\}')
        self.regexNoteMacro = re.compile(r'\{\{note\((.*?)\)\}\}')
        self.regexWarningMacro = re.compile(r'\{\{warning\((.*?)\)\}\}')
        self.regexImportantMacro = re.compile(r'\{\{important\((.*?)\)\}\}')
        self.regexAnyMacro = re.compile(r'\{\{(.*)\}\}')
        self.regexCodeBlock = re.compile(r'\A  ((.|\n)*)', re.MULTILINE)
        self.regexCollapse = re.compile(r'({{collapse\s?\(([^)]+)\))(.*)(}})', re.MULTILINE | re.DOTALL)
        self.regexParagraph = re.compile(r'p(\(+|(\)+)?>?|=)?\.', re.MULTILINE | re.DOTALL)
        self.regexCodeHighlight = re.compile(r'(<code\s?(class=\"(.*)\")?>).*(</code>)', re.MULTILINE | re.DOTALL)
        self.regexAttachment = re.compile(r'attachment:[\'\"“”‘’„”«»](.*)[\'\"“”‘’„”«»]', re.MULTILINE | re.DOTALL)

    def wiki_link(self, match):
        name = match.group(1)
        if len(match.groups()) > 1:
            text = match.group(2)
        else:
            text = name

        name = self.normalize(name).replace(' ', '_')
        return '[{}]({})'.format(text, name)

    def normalize(self, title):
        title = title.replace("ß", "ss")
        title = title.replace("ä", "ae")
        title = title.replace("ö", "oe")
        title = title.replace("ü", "ue")
        title = unicodedata.normalize('NFD', title).encode('ascii', 'ignore').decode('ascii')
        return title

    def convert(self, text):
        text = '\n\n'.join([re.sub(self.regexCodeBlock, r'<pre>\1</pre>', block) for block in text.split('\n\n')])

        collapseResults = re.findall(self.regexCollapse, text)
        if len(collapseResults) > 0:
            for i in range(0, len(collapseResults)):
                text = text.replace(collapseResults[i][0], "<details>")
                text = text.replace(collapseResults[i][2], "<summary>{}</summary> \n\n{}".format(collapseResults[i][1], collapseResults[i][2]))
                text = text.replace(collapseResults[i][3], "</details>")
        text = re.sub(self.regexParagraph, "", text)

        # convert from textile to markdown
        try:
            text = pypandoc.convert_text(text, 'markdown_strict', format='textile')

            # pandoc does not convert everything, notably the [[link|text]] syntax
            # is not handled. So let's fix that.

            # [[ wikipage | link_text ]] -> [link_text](wikipage)
            text = re.sub(self.regexWikiLinkWithText, self.wiki_link, text, re.MULTILINE | re.DOTALL)

            # [[ link_url ]] -> [link_url](link_url)
            text = re.sub(self.regexWikiLinkWithoutText, self.wiki_link, text, re.MULTILINE | re.DOTALL)

            # nested lists, fix at least the common issues
            text = text.replace("    \\#\\*", "    -")
            text = text.replace("    \\*\\#", "    1.")

            # Redmine is using '>' for blockquote, which is not textile
            text = text.replace("&gt; ", ">")

            # wiki note macros
            text = re.sub(self.regexTipMacro, r'---\n**TIP**: \1\n---\n', text, re.MULTILINE | re.DOTALL)
            text = re.sub(self.regexNoteMacro, r'---\n**NOTE**: \1\n---\n', text, re.MULTILINE | re.DOTALL)
            text = re.sub(self.regexWarningMacro, r'---\n**WARNING**: \1\n---\n', text, re.MULTILINE | re.DOTALL)
            text = re.sub(self.regexImportantMacro, r'---\n**IMPORTANT**: \1\n---\n', text, re.MULTILINE | re.DOTALL)

            # all other macros
            text = re.sub(self.regexAnyMacro, r'\1', text, re.MULTILINE | re.DOTALL)

            # attachments in notes
            text = re.sub(self.regexAttachment, r"\n\n*(Merged from Redmine, please check first note for attachment named **\1**)*", text, re.MULTILINE | re.DOTALL)

            # code highlight
            codeHighlights = re.findall(self.regexCodeHighlight, text)
            if len(codeHighlights) > 0:
                for i in range(0, len(codeHighlights)):
                    text = text.replace(codeHighlights[i][0], "\n```{}".format(codeHighlights[i][2].lower()))
                    text = text.replace(codeHighlights[i][3], "\n```")
        except RuntimeError as e:
            return False
        return text

class WikiPageConverter():
    """
    TODO:

    * set author email address in git commit
    * adjust issue numbers in links in case they do not match ("#123")
    * check links to commits ("commit:01234abc") or changesets ("r123")
    * make all wiki pages filenames lower-case and fix all links
    * tables are sometimes not converted correctly.
    * fix anything else that pandoc does not convert correctly.

    NOTE: This was tested with pandoc 1.17.0.2 - it may not work as nice
          (or badly? :-)) with other versions.

    Redmine's Textile:
    http://www.redmine.org/projects/redmine/wiki/RedmineTextFormattingTextile
    """

    def __init__(self, local_repo_path):
        self.repo_path = local_repo_path
        self.repo = Repo(local_repo_path)

        # make sure we use at least version 17 of pandoc
        # TODO: fix this test, it will not work properly for version 1.2 or 1.100
        version = pypandoc.get_pandoc_version()
        if (version < "1.17"):
            log.error('You need at least pandoc 1.17.0, download from http://pandoc.org/installing.html')
            exit(1)

        self.textile_converter = TextileConverter()

    def convert(self, redmine_page):
        title = self.textile_converter.normalize(redmine_page["title"])
        if (title == 'Wiki'):
            title = 'home'
        print("Converting {} ({} version {})".format(title, redmine_page["title"], redmine_page["version"]))

        text = redmine_page.get('text', "")

        # create a copy of the original page (for comparison, will not be committed)
        file_name = title + ".textile"
        with open(self.repo_path + "/" + file_name, mode='wt', encoding='utf-8') as fd:
            print(text, file=fd)

        # replace some contents
        text = text.replace("{{lastupdated_at}}", redmine_page["updated_on"])
        text = text.replace("{{lastupdated_by}}", redmine_page["author"]["name"])
        text = text.replace("[[PageOutline]]", "")
        text = text.replace("{{>toc}}", "")

        text = self.textile_converter.convert(text)

        # save file with author/date
        file_name = title + ".md"
        with open(self.repo_path + "/" + file_name, mode='wt', encoding='utf-8') as fd:
            print(text.replace('\n', "\n"), file=fd)

        # todo: check for attachments
        # todo: upload attachments

        if redmine_page["comments"]:
            commit_msg = redmine_page["comments"] + " (" + title + " v" + str(redmine_page["version"]) + ")";
        else:
            commit_msg = title + ", version " + str(redmine_page["version"]);

        author = Actor(redmine_page["author"]["name"], "")
        time   = redmine_page["updated_on"].replace("T", " ").replace("Z", " +0000")

        self.repo.index.add([file_name])
        self.repo.index.commit(commit_msg, author=author, committer=author, author_date=time, commit_date=time)
