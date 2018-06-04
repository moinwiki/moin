# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moinwiki->DOM->moinwiki using moinwiki_in and moinwiki_out converters

It is merge of test_moinwiki_in and test_moinwiki_out, looks bad but works.

TODO: Failing tests are commented out and need to be fixed.
"""


import pytest
import re

from emeraldtree import ElementTree as ET

from MoinMoin.util.tree import moin_page, xlink, xinclude, html
# from MoinMoin.converter.moinwiki_in import Converter as conv_in
from MoinMoin.converter.moinwiki19_in import ConverterFormat19 as conv_in
from MoinMoin.converter.moinwiki_out import Converter as conv_out


class TestConverter(object):

    input_namespaces = 'xmlns="{0}" xmlns:page="{1}" xmlns:xlink="{2}" xmlns:xinclude="{3}" xmlns:html="{4}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace)

    namespaces = {
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink',
        xinclude.namespace: 'xinclude',
        html.namespace: 'html',
    }
    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    def test_base(self):
        data = [
            (u'Text', 'Text\n'),
            (u"Text\n\nText\n", 'Text\n\nText\n'),
            (u"----\n-----\n------\n", '----\n-----\n------\n'),
            (u"'''strong'''\n", "'''strong'''\n"),
            (u"''emphasis''\n", "''emphasis''\n"),
            # extraneous x required below to prevent IndexError, side effect of serializer
            (u"{{{{{x\nblockcode\n}}}}}\n", "{{{{{x\nblockcode\n}}}}}\n"),
            (u"`monospace`\n", '`monospace`\n'),
            (u"--(stroke)--\n", '--(stroke)--\n'),
            (u"__underline__\n", '__underline__\n'),
            (u"~+larger+~\n", '~+larger+~\n'),
            (u"~-smaller-~\n", '~-smaller-~\n'),
            (u"^super^script\n", '^super^script\n'),
            (u",,sub,,script\n", ',,sub,,script\n'),
            (u"#ANY any", "#ANY any\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_comments(self):
        data = [
            (u"/* simple inline */", u"/* simple inline */"),
            (u"text /* text ''with '''markup''''' */ text", u"text /* text ''with '''markup''''' */ text"),
            (u"## block 1\n\n## block 2", u"## block 1\n\n## block 2"),

            # \n is omitted from output because serialize method (see below) joins adjacent text children
            (u"## block line 1\n## block line 2\n\n", u"## block line 1## block line 2\n\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macros(self):
        data = [
            (u"<<Anchor(anchorname)>>", '<<Anchor(anchorname)>>\n'),
            # (u"<<MonthCalendar(,,12)>>", '<<MonthCalendar(,,12)>>\n'), # MonthCalendar macro not implemented
            (u"<<FootNote(test)>>", "<<FootNote(test)>>\n"),
            (u"<<TableOfContents(2)>>", "<<TableOfContents(2)>>\n"),
            (u"<<TeudView()>>", "<<TeudView()>>\n"),
            (u"||<<TeudView()>>||", "||<<TeudView()>>||\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'[[SomePage#subsection|subsection of Some Page]]', '[[SomePage#subsection|subsection of Some Page]]\n'),
            (u'[[SomePage|{{attachment:samplegraphic.png}}|target=_blank]]', '[[SomePage|{{/samplegraphic.png}}|target="_blank"]]\n'),
            (u'[[../SisterPage|link text]]', '[[../SisterPage|link text]]\n'),
            (u'[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=_blank]]', '[[http://static.moinmo.in/logos/moinmoin.png|{{/samplegraphic.png}}|target="_blank"]]\n'),
            (u'[[http://moinmo.in/|MoinMoin Wiki|class="green dotted", accesskey=1]]', '[[http://moinmo.in/|MoinMoin Wiki|accesskey="1",class="green dotted"]]\n'),
            # interwiki
            # TODO: should this obsolete (1.9.x) form be made to work?
            # (u'[[MoinMoin:MoinMoinWiki|MoinMoin Wiki|&action=diff,&rev1=1,&rev2=2]]', '[[MoinMoin:MoinMoinWiki?action=diff,&rev1=1,&rev2=2|MoinMoin Wiki]]\n'),
            (u'[[MeatBall:InterWiki]]', '[[MeatBall:InterWiki]]'),
            (u'[[MeatBall:InterWiki|InterWiki page on MeatBall]]', '[[MeatBall:InterWiki|InterWiki page on MeatBall]]'),

            # TODO: attachments should be converted within import19.py and support removed from moin2
            # Note: old style attachments are converted to new style sub-item syntax; "&do-get" is appended to link and where it is ignored
            (u'[[attachment:HelpOnImages/pineapple.jpg|a pineapple|&do=get]]', '[[/HelpOnImages/pineapple.jpg?do=get|a pineapple]]\n'),
            (u'[[attachment:filename.txt]]', '[[/filename.txt]]\n'),
            # test parameters
            (u'[[SomePage|Some Page|target=_blank]]', '[[SomePage|Some Page|target="_blank"]]\n'),
            (u'[[SomePage|Some Page|download=MyItem,title=Download]]', '[[SomePage|Some Page|download="MyItem",title="Download"]]\n'),
            (u'[[SomePage|Some Page|download="MyItem",title="Download"]]', '[[SomePage|Some Page|download="MyItem",title="Download"]]\n'),
            (u'[[SomePage|Some Page|class=orange,accesskey=1]]', '[[SomePage|Some Page|accesskey="1",class="orange"]]\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u" * A\n * B\n  1. C\n  1. D\n   I. E\n   I. F\n", ' * A\n * B\n   1. C\n   1. D\n      I. E\n      I. F\n'),
            (u" * A\n  1. C\n   I. E\n", ' * A\n   1. C\n      I. E\n'),
            (u" * A\n  1. C\n  1. D\n", ' * A\n   1. C\n   1. D\n'),
            (u" i. E\n i. F\n", " i. E\n i. F\n"),
            (u" i.#11 K\n i. L\n", " i.#11 K\n i. L\n"),
            (u" 1.#11 eleven\n 1. twelve\n", " 1.#11 eleven\n 1. twelve\n"),
            (u" A:: B\n :: C\n :: D\n", ' A::\n :: B\n :: C\n :: D\n'),
            (u" A::\n :: B\n :: C\n :: D\n", ' A::\n :: B\n :: C\n :: D\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"||A||B||<|2>D||\n||||C||\n",
             u'||A||B||<rowspan="2">D||\n||<colspan="2">C||\n'),
            (u"||'''A'''||'''B'''||'''C'''||\n||1      ||2      ||3     ||\n",
             u"||'''A'''||'''B'''||'''C'''||\n||1      ||2      ||3     ||\n"),
            (u"||<|2> cell spanning 2 rows ||cell in the 2nd column ||\n||cell in the 2nd column of the 2nd row ||\n||<-2>test||\n||||test||",
             u'||<rowspan="2"> cell spanning 2 rows ||cell in the 2nd column ||\n||cell in the 2nd column of the 2nd row ||\n||<colspan="2">test||\n||<colspan="2">test||\n'),
            (u'|| narrow ||<99%> wide ||',
             u'|| narrow ||<style="width: 99%;"> wide ||\n'),
            (u'|| narrow ||<:> wide ||',
             u'|| narrow ||<style="text-align: center;"> wide ||\n'),
            (u'||table 1||\n\n||table 2||',
             u'||table 1||\n\n||table 2||'),
            (u'||<#FF8080> red ||<#80FF80> green ||<#8080FF> blue ||',
             u'||<style="background-color: #FF8080;"> red ||<style="background-color: #80FF80;"> green ||<style="background-color: #8080FF;"> blue ||\n'),
            (u'|| normal ||<style="font-weight: bold;"> bold ||<style="color: #FF0000;"> red ||<style="color: #FF0000; font-weight: bold;"> boldred ||',
             u'|| normal ||<style="font-weight: bold;"> bold ||<style="color: #FF0000;"> red ||<style="color: #FF0000; font-weight: bold;"> boldred ||\n'),
            (u'||<style="background-color: red;"> red ||<style="background-color: green;"> green ||<style="background-color: blue;"> blue ||',
             u'||<style="background-color: red;"> red ||<style="background-color: green;"> green ||<style="background-color: blue;"> blue ||\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            (u'{{png}}', '{{png}}\n'),
            (u'{{png|png}}', '{{png|png}}\n'),  # alt text same as default test
            (u'{{png|my png}}', '{{png|my png}}\n'),
            # output attributes will always be quoted, even if input is not quoted
            (u'{{png|my png|width=100}}', '{{png|my png|width="100"}}\n'),
            (u'{{png|my png|&w=100"}}', '{{png|my png|&w=100}}\n'),
            (u'{{png||width="100"}}', '{{png||width="100"}}\n'),
            (u"{{drawing:anywikitest.adraw}}", '{{drawing:anywikitest.adraw}}\n'),
            (u"{{http://static.moinmo.in/logos/moinmoin.png}}\n", '{{http://static.moinmo.in/logos/moinmoin.png}}\n'),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text}}\n', '{{http://static.moinmo.in/logos/moinmoin.png|alt text}}\n'),
            # output sequence of height, width, class may not be the same as input, so here we test only one attribute at a time to avoid random test failures
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|height="150"}}\n', '{{http://static.moinmo.in/logos/moinmoin.png|alt text|height="150"}}\n'),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|width="100"}}', '{{http://static.moinmo.in/logos/moinmoin.png|alt text|width="100"}}\n'),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|class="right"}}', '{{http://static.moinmo.in/logos/moinmoin.png|alt text|class="right"}}\n'),
            # Note: old style attachments are converted to new style sub-item syntax
            (u'{{attachment:image.png}}', '{{/image.png}}\n'),
            (u'{{attachment:image.png|alt text}}', '{{/image.png|alt text}}\n'),
            (u'{{attachment:image.png|alt text|height="150"}}', '{{/image.png|alt text|height="150"}}\n'),

        ]
        for i in data:
            yield (self.do, ) + i

    def test_page(self):
        pytest.skip("please help fixing moin wiki round trip tests")  # XXX TODO
        data = [
            (u"""
This page aims to introduce the most important elements of MoinMoin``'s syntax at a glance, showing first the markup verbatim and then how it is rendered by the wiki engine. Additionally, you'll find links to the relative help pages. Please note that some of the features depend on your configuration.

<<TableOfContents()>>

= Headings and table of contents =
'''''see:''' HelpOnHeadlines''
{{{
Table of contents:
<<TableOfContents()>>

Table of contents (up to 2nd level headings only):
<<TableOfContents(2)>>

= heading 1st level =
== heading 2nd level ==
=== heading 3rd level ===
==== heading 4th level ====
===== heading 5th level =====
====== no heading 6th level ======
}}}
{{{#!wiki
Table of contents:
<<TableOfContents()>>

Table of contents (up to 2nd level headings only):
<<TableOfContents(2)>>

= heading 1st level =
== heading 2nd level ==
=== heading 3rd level ===
==== heading 4th level ====
===== heading 5th level =====
====== no heading 6th level ======
}}}

= Text Formatting =
'''''see:''' HelpOnFormatting''
||<rowbgcolor="#ffffcc" width="50%"> '''Markup''' || '''Result'''   ||
||  `''italic''`     || ''italic''       ||
||  `'''bold'''`     || '''bold'''       ||
||  {{{`monospace`}}} || `monospace`  ||
||  `{{{code}}}`     || {{{code}}}       ||
||  `__underline__`  || __underline__   ||
||  `^super^script`  || ^super^script    ||
||  `,,sub,,script`  || ,,sub,,script    ||
||  `~-smaller-~`    || ~-smaller-~     ||
||  `~+larger+~`     || ~+larger+~       ||
|| `--(stroke)--`    || --(stroke)--     ||


= Hyperlinks =
'''''see:''' HelpOnLinking''


== Internal Links ==
||<rowbgcolor="#ffffcc" width="50%"> '''Markup''' || '''Result''' ||
|| `FrontPage` || FrontPage ||
|| `[[FrontPage]]` || [[FrontPage]] ||
|| `HelpOnEditing/SubPages` || HelpOnEditing/SubPages ||
|| `/SubPage` || /SubPage ||
|| `../SiblingPage` || ../SiblingPage ||
|| `[[FrontPage|named link]]` || [[FrontPage|named link]] ||
|| `[[#anchorname]]` || [[#anchorname]] ||
|| `[[#anchorname|description]]` || [[#anchorname|description]] ||
|| `[[PageName#anchorname]]` || [[PageName#anchorname]] ||
|| `[[PageName#anchorname|description]]` || [[PageName#anchorname|description]] ||
|| `[[attachment:filename.txt]]` || [[attachment:filename.txt]] ||


== External Links ==
||<rowbgcolor="#ffffcc" width="50%"> '''Markup''' || '''Result''' ||
|| `http://moinmo.in/` || http://moinmo.in/ ||
|| `[[http://moinmo.in/]]` || [[http://moinmo.in/]] ||
|| `[[http://moinmo.in/|MoinMoin Wiki]]` || [[http://moinmo.in/|MoinMoin Wiki]] ||
|| `[[http://static.moinmo.in/logos/moinmoin.png]]` || [[http://static.moinmo.in/logos/moinmoin.png]] ||
|| `{{http://static.moinmo.in/logos/moinmoin.png}}` || {{http://static.moinmo.in/logos/moinmoin.png}} ||
|| `[[http://static.moinmo.in/logos/moinmoin.png|moinmoin.png]]` || [[http://static.moinmo.in/logos/moinmoin.png|moinmoin.png]] ||
|| `MeatBall:InterWiki` || MeatBall:InterWiki ||
|| `[MeatBall:InterWiki|InterWiki page on MeatBall]]` || [[MeatBall:InterWiki|InterWiki page on MeatBall]] ||
|| `[[file://///server/share/filename%20with%20spaces.txt|link to filename.txt]]` || [[file://///servername/share/full/path/to/file/filename%20with%20spaces.txt|link to file filename with spaces.txt]] ||
|| `user@example.com` || user@example.com ||



== Avoid or Limit Automatic Linking ==
||<rowbgcolor="#ffffcc" width="50%"> '''Markup''' || '''Result''' ||
|| `Wiki''''''Name` || Wiki''''''Name ||
|| `Wiki``Name` || Wiki``Name ||
|| `!WikiName` || !WikiName ||
|| `WikiName''''''s` || WikiName''''''s ||
|| {{{WikiName``s}}} || WikiName``s ||
|| `http://www.example.com` || `http://www.example.com` ||
|| `[[http://www.example.com/]]notlinked` || [[http://www.example.com/]]notlinked ||


= Drawings =
'''''see:''' HelpOnDrawings''
== TWikiDraw ==
 {{drawing:myexample}}

== AnyWikiDraw ==
 {{drawing:myexample.adraw}}

= Blockquotes and Indentations =
{{{
 indented text
  text indented to the 2nd level
}}}
 indented text
  text indented to the 2nd level

= Lists =
'''''see:''' HelpOnLists''
== Unordered Lists ==
{{{
 * item 1

 * item 2 (preceding white space)
  * item 2.1
   * item 2.1.1
 * item 3
  . item 3.1 (bulletless)
 . item 4 (bulletless)
  * item 4.1
   . item 4.1.1 (bulletless)
}}}
 * item 1

 * item 2 (preceding white space)
  * item 2.1
   * item 2.1.1
 * item 3
  . item 3.1 (bulletless)
 . item 4 (bulletless)
  * item 4.1
   . item 4.1.1 (bulletless)

== Ordered Lists ==
=== with Numbers ===
{{{
 1. item 1
   1. item 1.1
   1. item 1.2
 1. item 2
}}}
 1. item 1
   1. item 1.1
   1. item 1.2
 1. item 2

=== with Roman Numbers ===
{{{
 I. item 1
   i. item 1.1
   i. item 1.2
 I. item 2
}}}
 I. item 1
   i. item 1.1
   i. item 1.2
 I. item 2

=== with Letters ===
{{{
 A. item A
   a. item A. a)
   a. item A. b)
 A. item B
}}}
 A. item A
   a. item A. a)
   a. item A. b)
 A. item B

== Definition Lists ==
{{{
 term:: definition
 object::
 :: description 1
 :: description 2
}}}
 term:: definition
 object::
 :: description 1
 :: description 2

= Horizontal Rules =
'''''see:''' HelpOnRules''
{{{
----
-----
------
-------
--------
---------
----------
}}}
----
-----
------
-------
--------
---------
----------


= Tables =
'''''see:''' HelpOnTables''
== Tables ==
{{{
||'''A'''||'''B'''||'''C'''||
||1      ||2      ||3      ||
}}}
||'''A'''||'''B'''||'''C'''||
||1      ||2      ||3      ||

== Cell Width ==
{{{
||minimal width ||<99%>maximal width ||
}}}
||minimal width ||<99%>maximal width ||

== Spanning Rows and Columns  ==
{{{
||<|2> cell spanning 2 rows ||cell in the 2nd column ||
||cell in the 2nd column of the 2nd row ||
||<-2> cell spanning 2 columns ||
||||use empty cells as a shorthand ||
}}}
||<|2> cell spanning 2 rows ||cell in the 2nd column ||
||cell in the 2nd column of the 2nd row ||
||<-2> cell spanning 2 columns ||
||||use empty cells as a shorthand ||

== Alignment of Cell Contents ==
{{{
||<^|3> top (combined) ||<:99%> center (combined) ||<v|3> bottom (combined) ||
||<)> right ||
||<(> left ||
}}}
||<^|3> top (combined) ||<:99%> center (combined) ||<v|3> bottom (combined) ||
||<)> right ||
||<(> left ||

== Coloured Table Cells ==
{{{
||<#0000FF> blue ||<#00FF00> green    ||<#FF0000> red    ||
||<#00FFFF> cyan ||<#FF00FF> magenta  ||<#FFFF00> yellow ||
}}}
||<#0000FF> blue ||<#00FF00> green    ||<#FF0000> red    ||
||<#00FFFF> cyan ||<#FF00FF> magenta  ||<#FFFF00> yellow ||

== HTML-like Options for Tables ==
{{{
||A ||<rowspan="2"> like <|2> ||
||<bgcolor="#00FF00"> like <#00FF00> ||
||<colspan="2"> like <-2>||
}}}
||A ||<rowspan="2"> like <|2> ||
||<bgcolor="#00FF00"> like <#00FF00> ||
||<colspan="2"> like <-2>||

= Macros and Variables =
== Macros ==
'''''see:''' HelpOnMacros''
 * <<Anchor(anchorname)>>`<<Anchor(anchorname)>>` inserts a link anchor `anchorname`
 * `<<BR>>` inserts a hard line break
 * `<<FootNote(Note)>>` inserts a footnote saying `Note`
 * `<<Include(HelpOnMacros/Include)>>` inserts the contents of the page `HelpOnMacros/Include` inline
 * `<<MailTo(user AT example DOT com)>>` obfuscates the email address `user@example.com` to users not logged in

== Variables ==
'''''see:''' HelpOnVariables''
 * `@``SIG``@` inserts your login name and timestamp of modification
 * `@``TIME``@` inserts date and time of modification

= Smileys and Icons =
'''''see:''' HelpOnSmileys''
<<ShowSmileys>>

= Parsers =
'''''see:''' HelpOnParsers''
== Verbatim Display ==
{{{{
{{{
def hello():
    print "Hello World!"
}}}
}}}}

{{{
def hello():
    print "Hello World!"
}}}

== Syntax Highlighting ==
{{{{
{{{#!highlight python
def hello():
    print "Hello World!"
}}}
}}}}

{{{#!highlight python
def hello():
    print "Hello World!"
}}}

== Using the wiki parser with css classes ==
{{{{
{{{#!wiki red/solid
This is wiki markup in a '''div''' with __css__ `class="red solid"`.
}}}
}}}}

{{{#!wiki red/solid
This is wiki markup in a '''div''' with __css__ `class="red solid"`.
}}}

= Admonitions =
'''''see:''' HelpOnAdmonitions''

{{{{
{{{#!wiki caution
'''Don't overuse admonitions'''

Admonitions should be used with care. A page riddled with admonitions will look restless and will be harder to follow than a page where admonitions are used sparingly.
}}}
}}}}

{{{#!wiki caution
'''Don't overuse admonitions'''

Admonitions should be used with care. A page riddled with admonitions will look restless and will be harder to follow than a page where admonitions are used sparingly.
}}}


= Comments =
'''''see:''' HelpOnComments''

{{{
Click on "Comments" in edit bar to toggle the /* comments */ visibility.
}}}

Click on "Comments" in edit bar to toggle the /* comments */ visibility.

{{{{
{{{#!wiki comment/dotted
This is a wiki parser section with class "comment dotted" (see HelpOnParsers).

Its visibility gets toggled the same way.
}}}
}}}}

{{{#!wiki comment/dotted
This is a wiki parser section with class "comment dotted" (see HelpOnParsers).

Its visibility gets toggled the same way.
}}}""", """ """),
        ]
        for i in data:
            yield (self.do, ) + i

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv_in(input, 'text/x.moin.wiki;charset=utf-8', **args)
        out = self.conv_out(self.handle_input(self.serialize(out)), **args)
        # assert self.handle_output(out) == output
        assert self.handle_output(out).strip() == output.strip()  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
