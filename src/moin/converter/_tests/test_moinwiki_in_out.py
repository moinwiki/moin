# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moinwiki->DOM->moinwiki using moinwiki_in and moinwiki_out converters

It is merge of test_moinwiki_in and test_moinwiki_out, looks bad but works.

TODO: Failing tests are commented out and need to be fixed.
"""

import pytest

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.util.tree import moin_page, xlink, xinclude, html
from moin.converter.moinwiki_in import Converter as conv_in
from moin.converter.moinwiki_out import Converter as conv_out


class TestConverter(object):

    input_namespaces = 'xmlns="{0}" xmlns:page="{1}" xmlns:xlink="{2}" xmlns:xinclude="{3}" xmlns:html="{4}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace)

    namespaces = {
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink',
        xinclude.namespace: 'xinclude',
        html.namespace: 'html',
    }
    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        (u'Text', 'Text\n'),
        (u"Text\n\nText\n", 'Text\n\nText\n'),
        (u"----\n-----\n------\n", '----\n-----\n------\n'),
        (u"'''strong or bold'''\n", "'''strong or bold'''\n"),
        (u"''emphasis or italic''\n", "''emphasis or italic''\n"),
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

    @pytest.mark.parametrize('input,output', data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (u"/* simple inline */", u"/* simple inline */"),
        (u"text /* text ''with '''markup''''' */ text", u"text /* text ''with '''markup''''' */ text"),
        (u"## block 1\n\n## block 2", u"## block 1\n\n## block 2"),

        # \n is omitted from output because serialize method (see below) joins adjacent text children
        (u"## block line 1\n## block line 2\n\n", u"## block line 1## block line 2\n\n"),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_comments(self, input, output):
        self.do(input, output)

    data = [
        (u"""{{{\ndef hello():\n    print "Hello World!"\n}}}""", u"""{{{\ndef hello():\n    print "Hello World!"\n}}}"""),
        (u"""{{{{\ndef hello():\n    print "Hello World!"\n}}}}""", u"""{{{{\ndef hello():\n    print "Hello World!"\n}}}}"""),
        (u'{{{#!highlight python\ndef hello():\n    print "Hello World!"\n}}}', u'{{{#!highlight python\ndef hello():\n    print "Hello World!"\n}}}'),
        (u"""{{{#!wiki red/solid\nThis is wiki markup in a '''div''' with __css__ `class="red solid"`.\n}}}""", u"""{{{#!wiki red/solid\nThis is wiki markup in a '''div''' with __css__ `class="red solid"`.\n}}}"""),
        (u'{{{#!creole\n|=X|1\n|=Y|123\n|=Z|12345\n}}}', '{{{#!creole\n|=X|1\n|=Y|123\n|=Z|12345\n}}}'),
        (u'{{{#!csv ,\nFruit,Color,Quantity\napple,red,5\nbanana,yellow,23\ngrape,purple,126\n}}}',
         u'{{{#!csv ,\nFruit,Color,Quantity\napple,red,5\nbanana,yellow,23\ngrape,purple,126\n}}}'),
        (u"{{{#!wiki caution\n '''Don't overuse admonitions'''\n}}}", "{{{#!wiki caution\n '''Don't overuse admonitions'''\n}}}"),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_nowiki(self, input, output):
        self.do(input, output)

    data = [
        (u"<<Anchor(anchorname)>>", '<<Anchor(anchorname)>>\n'),
        # (u"<<MonthCalendar(,,12)>>", '<<MonthCalendar(,,12)>>\n'), # MonthCalendar macro not implemented
        (u"<<FootNote(test)>>", "<<FootNote(test)>>\n"),
        (u"<<TableOfContents(2)>>", "<<TableOfContents(2)>>\n"),
        (u"<<TeudView()>>", "<<TeudView()>>\n"),
        (u"||<<TeudView()>>||", "||<<TeudView()>>||\n"),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_macros(self, input, output):
        self.do(input, output)

    # TODO: Both of the following tests should fail; the 5th and 7th lines of the output have
    # been dedented 3 spaces to create a passing test.
    # If the input is copied to a moinwiki document and a Convert to moinwiki is performed
    # the output will be equal to the input.
    data = [
        (u"""
    indented text
        text indented to the 2nd level
    first level
        second level
        second level again, will be combined with line above
        . second level as no bullet list
        continuation of no bullet list""", """
 . indented text
   . text indented to the 2nd level
 . first level
   . second level
second level again, will be combined with line above
   . second level as no bullet list
continuation of no bullet list"""),
        (u"""
 . indented text
   . text indented to the 2nd level
 . first level
   . second level
   second level again, will be combined with line above
   . second level as no bullet list
   continuation of no bullet list""", """
 . indented text
   . text indented to the 2nd level
 . first level
   . second level
second level again, will be combined with line above
   . second level as no bullet list
continuation of no bullet list"""),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_indented_text(self, input, output):
        self.do(input, output)

    data = [
        (u'[[Home]]', '[[Home]]'),
        (u'[[Home/subitem]]', '[[Home/subitem]]'),
        (u'[[/Subitem]]', '[[/Subitem]]'),
        (u'[[../Home]]', '[[../Home]]'),
        (u'[[SomePage#subsection|subsection of Some Page]]', '[[SomePage#subsection|subsection of Some Page]]\n'),
        (u'[[SomePage|{{attachment:samplegraphic.png}}|target=_blank]]',
         '[[SomePage|{{/samplegraphic.png}}|target="_blank"]]\n'),
        (u'[[../SisterPage|link text]]', '[[../SisterPage|link text]]\n'),
        (u'[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=_blank]]',
         '[[http://static.moinmo.in/logos/moinmoin.png|{{/samplegraphic.png}}|target="_blank"]]\n'),
        (u'[[https://moinmo.in/|MoinMoin Wiki|class="green dotted", accesskey=1]]',
         '[[https://moinmo.in/|MoinMoin Wiki|accesskey="1",class="green dotted"]]\n'),
        (u'[[https://moinmo.in/| |title="go there!"]]',
         '[[https://moinmo.in/||title="go there!"]]'),
        (u'[[file://///server/share/filename%20with%20spaces.txt|link to filename.txt]]',
         '[[file://///server/share/filename%20with%20spaces.txt|link to filename.txt]]'),
        # interwiki
        # TODO: should this obsolete (1.9.x) form be made to work?
        # (u'[[MoinMoin:MoinMoinWiki|MoinMoin Wiki|&action=diff,&rev1=1,&rev2=2]]', '[[MoinMoin:MoinMoinWiki?action=diff,&rev1=1,&rev2=2|MoinMoin Wiki]]\n'),
        (u'[[MeatBall:InterWiki]]', '[[MeatBall:InterWiki]]'),
        (u'[[MeatBall:InterWiki|InterWiki page on MeatBall]]', '[[MeatBall:InterWiki|InterWiki page on MeatBall]]'),
        # TODO: attachments should be converted within import19.py and support removed from moin2
        # Note: old style attachments are converted to new style sub-item syntax; "&do-get" is appended to link and ignored
        (u'[[attachment:HelpOnImages/pineapple.jpg|a pineapple|&do=get]]',
         '[[/HelpOnImages/pineapple.jpg?do=get|a pineapple]]\n'),
        (u'[[attachment:filename.txt]]', '[[/filename.txt]]\n'),
        # test parameters
        (u'[[SomePage|Some Page|target=_blank]]', '[[SomePage|Some Page|target="_blank"]]\n'),
        (u'[[SomePage|Some Page|download=MyItem,title=Download]]',
         '[[SomePage|Some Page|download="MyItem",title="Download"]]\n'),
        (u'[[SomePage|Some Page|download="MyItem",title="Download"]]',
         '[[SomePage|Some Page|download="MyItem",title="Download"]]\n'),
        (u'[[SomePage|Some Page|class=orange,accesskey=1]]', '[[SomePage|Some Page|accesskey="1",class="orange"]]\n'),
        (u'[[file://///server/share/filename%20with%20spaces.txt|link to filename.txt]]',
         '[[file://///server/share/filename%20with%20spaces.txt|link to filename.txt]]'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (u" * A\n * B\n  1. C\n  1. D\n   I. E\n   I. F\n", ' * A\n * B\n   1. C\n   1. D\n      I. E\n      I. F\n'),
        (u" * A\n  1. C\n   I. E\n", ' * A\n   1. C\n      I. E\n'),
        (u" * A\n  1. C\n  1. D\n", ' * A\n   1. C\n   1. D\n'),
        (u" . A\n  . C\n  . D\n", ' . A\n   . C\n   . D\n'),
        (u" i. E\n i. F\n", " i. E\n i. F\n"),
        (u" i.#11 K\n i. L\n", " i.#11 K\n i. L\n"),
        (u" 1.#11 eleven\n 1. twelve\n", " 1.#11 eleven\n 1. twelve\n"),
        (u" A:: B\n :: C\n :: D\n", ' A::\n :: B\n :: C\n :: D\n'),
        (u" A::\n :: B\n :: C\n :: D\n", ' A::\n :: B\n :: C\n :: D\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (u"||A||B||<|2>D||\n||||C||\n",
         u'||A||B||<rowspan="2">D||\n||<colspan="2">C||\n'),
        (u"||'''A'''||'''B'''||'''C'''||\n||1      ||2      ||3     ||\n",
         u"||'''A'''||'''B'''||'''C'''||\n||1      ||2      ||3     ||\n"),
        (
        u"||<|2> cell spanning 2 rows ||cell in the 2nd column ||\n||cell in the 2nd column of the 2nd row ||\n||<-2>test||\n||||test||",
        u'||<rowspan="2"> cell spanning 2 rows ||cell in the 2nd column ||\n||cell in the 2nd column of the 2nd row ||\n||<colspan="2">test||\n||<colspan="2">test||\n'),
        (u'|| narrow ||<99%> wide ||',
         u'|| narrow ||<style="width: 99%;"> wide ||\n'),
        (u'|| narrow ||<:> wide ||',
         u'|| narrow ||<style="text-align: center;"> wide ||\n'),
        (u'||table 1||\n\n||table 2||',
         u'||table 1||\n\n||table 2||'),
        (u'||<#FF8080> red ||<#80FF80> green ||<#8080FF> blue ||',
         u'||<style="background-color: #FF8080;"> red ||<style="background-color: #80FF80;"> green ||<style="background-color: #8080FF;"> blue ||\n'),
        (
        u'|| normal ||<style="font-weight: bold;"> bold ||<style="color: #FF0000;"> red ||<style="color: #FF0000; font-weight: bold;"> boldred ||',
        u'|| normal ||<style="font-weight: bold;"> bold ||<style="color: #FF0000;"> red ||<style="color: #FF0000; font-weight: bold;"> boldred ||\n'),
        (
        u'||<style="background-color: red;"> red ||<style="background-color: green;"> green ||<style="background-color: blue;"> blue ||',
        u'||<style="background-color: red;"> red ||<style="background-color: green;"> green ||<style="background-color: blue;"> blue ||\n'),
        (
        u'||<tableclass="moin-sortable">Fruit||Quantity||\n=====\n||Apple||2||\n||Orange||1||\n||Banana||4||\n=====\n||Total||7||',
        u'||<tableclass="moin-sortable">Fruit||Quantity||\n=====\n||Apple||2||\n||Orange||1||\n||Banana||4||\n=====\n||Total||7||'),
        (
        u'||<style="vertical-align: top;" rowspan="3"> top||<style="text-align: center; width: 99%;"> center||<style="vertical-align: bottom;" rowspan="3"> bottom||\n||<style="text-align: right;"> right||\n||<style="text-align: left;"> left||',
        u'||<style="vertical-align: top;" rowspan="3"> top||<style="text-align: center; width: 99%;"> center||<style="vertical-align: bottom;" rowspan="3"> bottom||\n||<style="text-align: right;"> right||\n||<style="text-align: left;"> left||'),
        (
        u'||<^|3> top ||<:99%> center ||<v|3> bottom ||\n||<)> right ||\n||<(> left ||',
        u'||<style="vertical-align: top;" rowspan="3"> top ||<style="text-align: center; width: 99%;"> center ||<style="vertical-align: bottom;" rowspan="3"> bottom ||\n||<style="text-align: right;"> right ||\n||<style="text-align: left;"> left ||'),
        (
        u'||<caption="My Table" tablewidth="30em">A ||<rowspan="2" > like <|2> ||\n||<bgcolor="#00FF00"> like <#00FF00> ||\n||<colspan="2"> like <-2>||',
        u'||<tablestyle="width: 30em;" caption="My Table">A ||<rowspan="2"> like <|2> ||\n||<style="background-color: #00FF00;"> like <#00FF00> ||\n||<colspan="2"> like <-2>||'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (u'{{png}}', '{{png}}\n'),
        (u'{{png|png}}', '{{png|png}}\n'),  # alt text same as default test
        (u'{{png|my png}}', '{{png|my png}}\n'),
        (u'{{{{video.mp4}}}}', '{{{{video.mp4}}}}\n'),
        (u'{{{{audio.mp3}}}}', '{{{{audio.mp3}}}}\n'),
        # output attributes will always be quoted, even if input is not quoted
        (u'{{png|my png|width=100}}', '{{png|my png|width="100"}}\n'),
        (u'{{png|my png|&w=100"}}', '{{png|my png|&w=100}}\n'),
        (u'{{png||width="100"}}', '{{png||width="100"}}\n'),
        (u"{{drawing:anywikitest.adraw}}", '{{drawing:anywikitest.adraw}}\n'),
        (u"{{http://static.moinmo.in/logos/moinmoin.png}}\n", '{{http://static.moinmo.in/logos/moinmoin.png}}\n'),
        (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text}}\n',
         '{{http://static.moinmo.in/logos/moinmoin.png|alt text}}\n'),
        # output sequence of height, width, class may not be the same as input, so here we test only one attribute at a time to avoid random test failures
        (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|height="150"}}\n',
         '{{http://static.moinmo.in/logos/moinmoin.png|alt text|height="150"}}\n'),
        (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|width="100"}}',
         '{{http://static.moinmo.in/logos/moinmoin.png|alt text|width="100"}}\n'),
        (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|class="right"}}',
         '{{http://static.moinmo.in/logos/moinmoin.png|alt text|class="right"}}\n'),
        # Note: old style attachments are converted to new style sub-item syntax
        (u'{{attachment:image.png}}', '{{/image.png}}\n'),
        (u'{{attachment:image.png|alt text}}', '{{/image.png|alt text}}\n'),
        (u'{{attachment:image.png|alt text|height="150"}}', '{{/image.png|alt text|height="150"}}\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_object(self, input, output):
        self.do(input, output)

    data = [
        (u'Images are aligned to bottom {{png}} of text by default.',
         'Images are aligned to bottom {{png}} of text by default.'),
        (u'This image is the big logo floated to the right: {{svg|my svg|class="right"}}',
         'This image is the big logo floated to the right: {{svg|my svg|class="right"}}'),
        (u'Image aligned to top of text. {{jpeg||&w=75 class="top"}}',
         'Image aligned to top of text. {{jpeg||&w=75 class="top"}}'),
        (u'Image aligned to middle of text. {{http://static.moinmo.in/logos/moinmoin.png||class=middle}}',
         'Image aligned to middle of text. {{http://static.moinmo.in/logos/moinmoin.png||class="middle"}}'),
        (u'Transclude an HTTPS web page: <<BR>>{{https://moinmo.in||width="800"}}',
         'Transclude an HTTPS web page: <<BR>>{{https://moinmo.in||width="800"}}'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_transclusions(self, input, output):
        self.do(input, output)

    data_input = u"""
||Markup||Display||Emotion   ||
=====
||`X-(` || X-(   ||angry     ||
||`:D`  || :D    ||biggrin   ||
||`>:>` || >:>   ||devil     ||
||`<:(` || <:(   ||frown     ||
||`:\`  || :\    ||ohwell    ||
||`:o`  || :o    ||redface   ||
||`:-(` || :-(   ||sad       ||
||`:(`  || :(    ||sad       ||
||`:)`  || :)    ||smile     ||
||`B)`  || B)    ||smile2    ||
||`:))` || :))   ||smile3    ||
||`;)`  || ;)    ||smile4    ||
||`|)`  || |)    ||tired     ||
||`|-)` || |-)   ||tired     ||
||`:-?` || :-?   ||tongue    ||
||`/!\` || /!\   ||alert     ||
||`<!>` || <!>   ||attention ||
||`(./)`|| (./)  ||checkmark ||
||`{X}` || {X}   ||icon-error||
||`{i}` || {i}   ||icon-info ||
||`(!)` || (!)   ||idea      ||
||`{1}` || {1}   ||prio1     ||
||`{2}` || {2}   ||prio2     ||
||`{3}` || {3}   ||prio3     ||
||`{*}` || {*}   ||star_on   ||
||`{o}` || {o}   ||star_off  ||
||`{OK}`|| {OK}  ||thumbs-up ||
"""
    data = [(data_input, data_input)]

    @pytest.mark.parametrize('input,output', data)
    def test_smileys(self, input, output):
        self.do(input, output)

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', result)

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv_in(input, 'text/x.moin.wiki;charset=utf-8', **args)
        out = self.conv_out(self.handle_input(self.serialize_strip(out)), **args)
        # assert self.handle_output(out) == output
        assert self.handle_output(out).strip() == output.strip()  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
