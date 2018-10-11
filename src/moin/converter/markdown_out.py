# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2018 MoinMoin:RogerHaase - modified moinwiki_out.py for markdown
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Markdown markup output converter

Converts an internal document tree into markdown markup.
"""


from __future__ import absolute_import, division

import urllib

from . import ElementException

from moin.util.tree import moin_page, xlink, xinclude, html
from moin.util.iri import Iri

from emeraldtree import ElementTree as ET

from re import findall, sub

from werkzeug.utils import unescape

from . import default_registry
from moin.util.mime import Type, type_moin_document


class Markdown(object):
    """
    Markdown syntax elements
    It's dummy
    """
    h = u'#'
    a_open = u'<'
    a_desc_open = '('
    a_desc_close = ')'
    a_close = u'>'
    comment_open = '<!-- '
    comment_close = ' -->'
    verbatim_open = u'    '  # * 3
    verbatim_close = u'    '  # * 3
    monospace = u'`'
    strong = u"**"
    emphasis = u"*"
    underline_open = u'<u>'
    underline_close = u'</u>'
    samp_open = u'`'
    samp_close = u'`'
    stroke_open = u'<strike>'
    stroke_close = u'</strike>'
    table_marker = u'|'
    p = u'\n'
    linebreak = u'  '
    larger_open = u'<big>'
    larger_close = u'</big>'
    smaller_open = u'<small>'
    smaller_close = u'</small>'
    object_open = u'{{'
    object_close = u'}}'
    definition_list_marker = u':  '
    separator = u'----'
    # TODO: definition list
    list_type = {
        (u'definition', None): u'',
        (u'ordered', None): u'1.',
        (u'ordered', u'lower-alpha'): u'1.',
        (u'ordered', u'upper-alpha'): u'1.',
        (u'ordered', u'lower-roman'): u'1.',
        (u'ordered', u'upper-roman'): u'1.',
        (u'unordered', None): u'*',
        (u'unordered', u'no-bullet'): u'*',
        (None, None): u'::',
    }

    def __init__(self):
        pass


class Converter(object):
    """
    Converter application/x.moin.document -> text/x.moin.wiki
    """
    namespaces = {
        moin_page.namespace: 'moinpage',
        xinclude: 'xinclude',
    }

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __init__(self):
        self.list_item_labels = [u'', ]
        self.list_item_label = u''
        self.list_level = 0
        self.footnotes = []  # tuple of (name, text)
        self.footnote_number = 0  # incremented if a footnote name was not passed

    def __call__(self, root):
        self.status = ['text', ]
        self.last_closed = None
        self.list_item_label = []
        content = self.open(root)
        while '\n\n\n' in content:
            content = content.replace('\n\n\n', '\n\n')
        if self.footnotes:
            # add footnote definitions to end of content
            notes = []
            for name, txt in self.footnotes:
                notes.append(u'[^{0}]: {1}'.format(name, txt))
            notes = u'\n'.join(notes)
            content += u'\n\n' + notes + u'\n'
        return content

    def open_children(self, elem, join_char=u''):
        childrens_output = []
        for child in elem:
            if isinstance(child, ET.Element):
                # open function can change self.output
                childrens_output.append(self.open(child))
            else:
                ret = u''
                if self.status[-1] == "text":
                    if self.last_closed == "p":
                        ret = u'\n'
                if child == '\n' and getattr(elem, 'level', 0):
                    child = child + ' ' * (len(u''.join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))
                childrens_output.append(u'{0}{1}'.format(ret, child))
                self.last_closed = 'text'
        out = join_char.join(childrens_output)
        return out

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'open_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        # process odd things like xinclude
        return self.open_children(elem)

    def open_moinpage(self, elem):
        n = 'open_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            ret = f(elem)
            self.last_closed = elem.tag.name.replace('-', '_')
            return ret
        return self.open_children(elem)

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)
        if isinstance(href, Iri):
            href = unicode(href)
        href = href.split(u'wiki.local:')[-1]
        ret = href
        text = self.open_children(elem)
        if text:
            return u'[{0}]({1})'.format(text, href)
        if ret.startswith('wiki://'):
            # interwiki fixup
            ret = ret[7:]
            ret = ret.replace('/', ':', 1)
        return Markdown.a_open + ret + Markdown.a_close

    def open_moinpage_blockcode(self, elem):
        text = u''.join(elem.itertext())

        if elem.attrib.get(html.class_, None) == 'codehilite':
            return text

        lines = text.split('\n')
        ret = '\n' + Markdown.verbatim_open + ('\n' + Markdown.verbatim_open).join(lines)
        return '\n' + ret + '\n'

    def open_moinpage_block_comment(self, elem):
        # convert moin hidden comment markdown/html comment: ## some block comment
        return Markdown.comment_open + '\n'.join(elem) + Markdown.comment_close

    def open_moinpage_blockquote(self, elem):
        # blockquotes are generated by html_in (and maybe others), not by moinwiki_in
        # to achieve same look, we convert to bulletless unordered list
        ret = self.open_children(elem)
        ret = ret.strip()
        indented = []
        for line in ret.split('\n'):
            indented.append(u' > ' + line)
        return '\n' + '\n'.join(indented) + '\n'

    def open_moinpage_code(self, elem):
        ret = Markdown.monospace
        ret += u''.join(elem.itertext())
        ret += Markdown.monospace
        return ret

    def open_moinpage_div(self, elem):
        """
        Find and process div tags with special classes as needed.
        """
        if elem.attrib.get(html.class_, None) == 'toc':
            # we do not want expanded toc
            return '\n\n[TOC]\n\n'

        if elem.attrib.get(html.class_, None) == 'codehilite' and isinstance(elem[0][1], unicode):
            # in most cases, codehilite returns plain text blocks; return an indented block
            text = elem[0][1].split('\n')
            return '\n' + '\n'.join([u'    ' + x for x in text]) + '\n'

        childrens_output = self.open_children(elem)
        return '\n\n' + childrens_output + '\n\n'

    def open_moinpage_emphasis(self, elem):
        childrens_output = self.open_children(elem)
        return u"{0}{1}{2}".format(Markdown.emphasis, childrens_output, Markdown.emphasis)

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = Markdown.h * level + u' '
        ret += u''.join(elem.itertext())
        ret += u' {0}\n'.format(Markdown.h * level)
        return u'\n' + ret

    def open_moinpage_line_break(self, elem):
        return Markdown.linebreak

    def open_moinpage_list(self, elem):
        label_type = elem.get(moin_page.item_label_generate, None), elem.get(moin_page.list_style_type, None)
        self.list_item_labels.append(Markdown.list_type.get(label_type, u'*'))
        self.list_level += 1
        ret = u''
        if self.status[-1] != 'text' or self.last_closed:
            ret = u'\n'
        self.status.append('list')
        self.last_closed = None
        childrens_output = self.open_children(elem)
        list_start = elem.attrib.get(moin_page.list_start)
        if list_start:
            child_out1, child_out2 = childrens_output.split(u'.', 1)
            childrens_output = u'{0}.#{1}{2}'.format(child_out1, list_start, child_out2)
        self.list_item_labels.pop()
        self.list_level -= 1
        self.status.pop()
        if self.status[-1] == 'list':
            ret_end = u''
        else:
            ret_end = u'\n'
        return u"{0}{1}{2}".format(ret, childrens_output, ret_end)

    def open_moinpage_list_item(self, elem):
        self.list_item_label = self.list_item_labels[-1] + u' '
        return self.open_children(elem)

    def open_moinpage_list_item_label(self, elem):
        """Used for definition list terms"""
        ret = u''
        if self.list_item_labels[-1] == u'' or self.list_item_labels[-1] == Markdown.definition_list_marker:
            self.list_item_labels[-1] = Markdown.definition_list_marker
            self.list_item_label = self.list_item_labels[-1] + u' '
            ret = u'   ' * (len(u''.join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))
            if self.last_closed:
                ret = u'\n{0}'.format(ret)
        childrens_output = self.open_children(elem)
        return "\n{0}{1}".format(ret, childrens_output)

    def open_moinpage_list_item_body(self, elem):
        ret = u''
        if self.last_closed:
            ret = u'\n'
        ret += u'    ' * len(self.list_item_labels[:-2]) + self.list_item_label
        child_out = self.open_children(elem)
        if self.list_item_label[0] == Markdown.definition_list_marker[0]:
            child_out = u'\n    '.join(child_out.split('\n'))
        return ret + child_out

    def open_moinpage_note(self, elem):
        # used for moinwiki to markdown conversion; not used for broken markdown to markdown conversion
        class_ = elem.get(moin_page.note_class, u"")
        if class_:
            if class_ == "footnote":
                self.footnote_number += 1
                self.footnotes.append((self.footnote_number, self.open_children(elem)))
                return u'[^{0}]'.format(self.footnote_number)
        # moinwiki footnote placement is ignored; markdown cannot place footnotes in middle of document like moinwiki
        return u''

    def open_moinpage_nowiki(self, elem):
        """No support for moin features like highlight or nowiki within nowiki."""
        if isinstance(elem[0], ET.Element) and elem[0].tag.name == 'blockcode' and isinstance(elem[0][0], unicode):
            text = elem[0][0].split('\n')
            return '\n' + '\n'.join([u'    ' + x for x in text]) + '\n'
        return self.open_children(elem)

    def open_moinpage_object(self, elem):
        """
        Process moinwiki_in objects: {{transclusions}}  and <<Include(parameters,...)>>

        Transcluded objects are expanded in output because Markdown does not support transclusions.
        """
        href = elem.get(xlink.href, elem.get(xinclude.href, u''))
        if isinstance(href, Iri):
            href = unicode(href)
            href = urllib.unquote(href)
            if href.startswith('/+get/+'):
                href = href.split('/')[-1]
        href = href.split(u'wiki.local:')[-1]
        if len(elem) and isinstance(elem[0], unicode):
            # alt text for objects is enclosed within <object...>...</object>
            alt = elem[0]
        else:
            alt = elem.attrib.get(html.alt, u'')
        title = elem.attrib.get(html.title_, u'')
        if title:
            title = u'"{0}"'.format(title)
        ret = u'![{0}]({1} {2})'.format(alt, href, title)
        ret = ret.replace(' )', ')')
        return ret

    def open_moinpage_p(self, elem):
        if moin_page.class_ in elem.attrib and 'moin-error' in elem.attrib[moin_page.class_]:
            # ignore error messages inserted into DOM
            return u''

        self.status.append("p")
        ret = u""
        if self.status[-2] == 'text':
            if self.last_closed == 'text':
                ret = Markdown.p * 2 + self.open_children(elem) + Markdown.p
            elif self.last_closed:
                ret = Markdown.p + self.open_children(elem) + Markdown.p
            else:
                ret = self.open_children(elem) + Markdown.p
        elif self.status[-2] == 'table':
            if self.last_closed and self.last_closed != 'table_cell' and self.last_closed != 'table_row':
                ret = Markdown.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        elif self.status[-2] == 'list':  # TODO: still possible? <p> after <li> removed from moinwiki_in
            if self.last_closed and (
                self.last_closed != 'list_item' and self.last_closed != 'list_item_header' and
                self.last_closed != 'list_item_footer' and self.last_closed != 'list_item_label'):
                ret = Markdown.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        else:
            ret = self.open_children(elem)
        self.status.pop()
        return ret

    def open_moinpage_page(self, elem):
        self.last_closed = None
        ret = u''
        if len(self.status) > 1:
            self.status.append('text')
            childrens_output = self.open_children(elem)
            self.status.pop()
            return childrens_output

        self.status.append('text')
        childrens_output = self.open_children(elem)
        self.status.pop()
        return childrens_output

    def open_moinpage_body(self, elem):
        class_ = elem.get(moin_page.class_, u'').replace(u' ', u'/')
        if class_:
            ret = u' {0}\n'.format(class_)
        elif len(self.status) > 2:
            ret = u'\n'
        else:
            ret = u''
        childrens_output = self.open_children(elem)
        return u"{0}{1}".format(ret, childrens_output)

    def open_moinpage_samp(self, elem):
        # text {{{more text}}} end
        ret = Markdown.samp_open
        ret += u''.join(elem.itertext())
        ret += Markdown.samp_close
        return ret

    def open_moinpage_separator(self, elem):
        return u'\n----\n'

    def open_moinpage_span(self, elem):
        font_size = elem.get(moin_page.font_size, u'')
        baseline_shift = elem.get(moin_page.baseline_shift, u'')
        if font_size:
            return u"{0}{1}{2}".format(
                Markdown.larger_open if font_size == u"120%" else Markdown.smaller_open,
                self.open_children(elem),
                Markdown.larger_close if font_size == u"120%" else Markdown.smaller_close)
        if baseline_shift == u'super':
            return u'<sup>{0}</sup>'.format(u''.join(elem.itertext()))
        if baseline_shift == u'sub':
            return u'<sub>{0}</sub>'.format(u''.join(elem.itertext()))
        return u''.join(self.open_children(elem))

    def open_moinpage_del(self, elem):  # stroke or strike-through
        return Markdown.stroke_open + self.open_children(elem) + Markdown.stroke_close

    def open_moinpage_s(self, elem):  # s is used for stroke or strike by html_in
        return self.open_moinpage_del(elem)

    def open_moinpage_ins(self, elem):  # underline
        return Markdown.underline_open + self.open_children(elem) + Markdown.underline_close

    def open_moinpage_u(self, elem):  # underline via html_in
        return self.open_moinpage_ins(elem)

    def open_moinpage_strong(self, elem):
        ret = Markdown.strong
        return u"{0}{1}{2}".format(Markdown.strong, self.open_children(elem), Markdown.strong)

    def open_moinpage_table(self, elem):
        self.status.append('table')
        self.last_closed = None
        ret = self.open_children(elem)
        self.status.pop()
        # markdown tables must have headings
        if '----' not in ret:
            rows = ret.split('\n')
            header = rows[0][1:-1]  # remove leading and trailing |
            cells = header.split('|')
            marker = Markdown.table_marker + Markdown.table_marker.join(['----' for x in cells]) + Markdown.table_marker
            rows.insert(1, marker)
            ret = '\n'.join(rows)
        return u'\n' + ret + u'\n'

    def open_moinpage_table_header(self, elem):
        # used for reST to moinwiki conversion, maybe others that generate table head
        separator = []
        for th in elem[0]:
            if th.attrib.get(moin_page.class_, None) == 'center':
                separator.append(':----:')
            elif th.attrib.get(moin_page.class_, None) == 'left':
                separator.append(':-----')
            elif th.attrib.get(moin_page.class_, None) == 'right':
                separator.append('-----:')
            else:
                separator.append('------')
        separator = Markdown.table_marker.join(separator)
        ret = self.open_children(elem)
        ret = ret + u'{0}{1}{0}\n'.format(Markdown.table_marker, separator)
        return ret

    def open_moinpage_table_body(self, elem):
        ret = self.open_children(elem)
        return ret

    def open_moinpage_table_row(self, elem):
        ret = self.open_children(elem, join_char=Markdown.table_marker)
        return u'{0}{1}{0}\n'.format(Markdown.table_marker, ret)

    def open_moinpage_table_of_content(self, elem):
        return u"\n[TOC]\n"

    def open_xinclude(self, elem):
        """Processing of transclusions is similar to objects."""
        return self.open_moinpage_object(elem)


default_registry.register(Converter._factory, type_moin_document, Type("text/x-markdown"))
default_registry.register(Converter._factory, type_moin_document, Type('x-moin/format;name=markdown'))
