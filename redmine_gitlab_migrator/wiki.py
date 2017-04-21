import pypandoc
import logging
import re

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
        self.regexNonASCII = re.compile(r'[^a-zA-Z_0-9]')
        self.regexWikiLinkWithText = re.compile(r'\\\[\\\[\s*(.*?)\s*\|\s*(.*?)\s*\\\]\\\]')
        self.regexWikiLinkWithoutText = re.compile(r'\\\[\\\[\s*(.*?)\s*\\\]\\\]')
        self.regexTipMacro = re.compile(r'\{\{tip\((.*?)\)\}\}')
        self.regexNoteMacro = re.compile(r'\{\{note\((.*?)\)\}\}')
        self.regexWarningMacro = re.compile(r'\{\{warning\((.*?)\)\}\}')
        self.regexImportantMacro = re.compile(r'\{\{important\((.*?)\)\}\}')
        self.regexAnyMacro = re.compile(r'\{\{(.*)\}\}')

    def convert(self, text):
        # convert from textile to markdown
        text = pypandoc.convert(text, 'markdown_strict', format='textile')

        # pandoc does not convert everything, notably the [[link|text]] syntax
        # is not handled. So let's fix that.

        # [[ wikipage | link_text ]] -> [link_text](wikipage)
        text = re.sub(self.regexWikiLinkWithText, r'[\2](\1)', text, re.MULTILINE | re.DOTALL)

        # [[ link_url ]] -> [link_url](link_url)
        text = re.sub(self.regexWikiLinkWithoutText, r'[\1](\1)', text, re.MULTILINE | re.DOTALL)

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

        return text
