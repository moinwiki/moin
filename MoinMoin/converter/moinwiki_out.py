# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Moinwiki markup output converter

Converts an internal document tree into moinwiki markup.
"""


from __future__ import absolute_import, division

import urllib

from MoinMoin.util.tree import moin_page, xlink, xinclude, html
from MoinMoin.util.iri import Iri

from emeraldtree import ElementTree as ET

from re import findall, sub

from werkzeug.utils import unescape


class Moinwiki(object):
    """
    Moinwiki syntax elements
    It's dummy
    """
    h = u'='
    a_open = u'[['
    a_separator = u'|'
    a_close = u']]'
    verbatim_open = u'{'  # * 3
    verbatim_close = u'}'  # * 3
    monospace = u'`'
    strong = u"'''"
    emphasis = u"''"
    underline = u'__'
    samp_open = u'{{{'  # 3 brackets is only option for inline
    samp_close = u'}}}'
    stroke_open = u'--('
    stroke_close = u')--'
    table_marker = u'||'
    p = u'\n'
    linebreak = u'<<BR>>'
    larger_open = u'~+'
    larger_close = u'+~'
    smaller_open = u'~-'
    smaller_close = u'-~'
    object_open = u'{{'
    object_close = u'}}'
    definition_list_marker = u'::'
    separator = u'----'
    # TODO: definition list
    list_type = {
        (u'definition', None): u'',
        (u'ordered', None): u'1.',
        (u'ordered', u'lower-alpha'): u'a.',
        (u'ordered', u'upper-alpha'): u'A.',
        (u'ordered', u'lower-roman'): u'i.',
        (u'ordered', u'upper-roman'): u'I.',
        (u'unordered', None): u'*',
        (u'unordered', u'no-bullet'): u'.',
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

    supported_tag = {
        'moinpage': (
            'a',
            'blockcode',
            'break_line',
            'code',
            'div',
            'emphasis',
            'h',
            'list',
            'list_item',
            'list_item_label',
            'list_item_body',
            'nowiki',
            'p',
            'page',
            'separator',
            'span',
            'strong',
            'object',
            'table',
            'table_header',
            'table_footer',
            'table_body',
            'table_row',
            'table_cell',
        ),
        'xinclude': (
            'include',
        ),
    }

    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __init__(self):

        # TODO: create class containing all table attributes
        self.table_tableclass = u''
        self.table_tablestyle = u''
        self.table_rowsclass = u''
        self.table_rowsstyle = u''
        self.table_rowstyle = u''
        self.table_rowclass = u''

        self.list_item_labels = [u'', ]
        self.list_item_label = u''
        self.list_level = 0

        # 'text' - default status - <p> = '/n' and </p> = '/n'
        # 'table' - text inside table - <p> = '<<BR>>' and </p> = ''
        # 'list' - text inside list - <p> if after </p> = '<<BR>>' and </p> = ''
        # status added because of differences in interpretation of <p> in different places
    def __call__(self, root):
        self.status = ['text', ]
        self.last_closed = None
        self.list_item_label = []
        content = self.open(root)
        while '\n\n\n' in content:
            content = content.replace('\n\n\n', '\n\n')
        content = content[1:] if content.startswith('\n') else content
        return content

    def open_children(self, elem):
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
        out = u''.join(childrens_output)
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
        params = {}
        params['target'] = elem.get(html.target, None)
        params['title'] = elem.get(html.title_, None)
        params['download'] = elem.get(html.download, None)
        params['class'] = elem.get(html.class_, None)
        params['accesskey'] = elem.get(html.accesskey, None)
        # we sort so output order is predictable for tests
        params = u','.join([u'{0}="{1}"'.format(p, params[p]) for p in sorted(params) if params[p]])

        # XXX: We don't have Iri support for now
        if isinstance(href, Iri):
            href = unicode(href)
        # TODO: this can be done using one regex, can it?
        href = href.split(u'#')
        if len(href) > 1:
            href, fragment = href
        else:
            href, fragment = href[0], ''
        href = href.split(u'?')
        args = u''
        if len(href) > 1:
            # With normal
            args = u''.join([u'&' + s for s in findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$|)', href[1])])
        href = href[0].split(u'wiki.local:')[-1]
        if args:
            args = '?' + args[1:]
        if fragment:
            args += '#' + fragment
        text = self.open_children(elem)
        if text == href:
            text = u''
        ret = u'{0}{1}|{2}|{3}'.format(href, args, text, params)
        ret = ret.rstrip('|')
        if ret.startswith('wiki://'):
            # interwiki fixup
            ret = ret[7:]
            ret = ret.replace('/', ':', 1)
        return Moinwiki.a_open + ret + Moinwiki.a_close

    def open_moinpage_blockcode(self, elem):
        text = u''.join(elem.itertext())
        max_subpage_lvl = 3
        for s in findall(r'}+', text):
            if max_subpage_lvl <= len(s):
                max_subpage_lvl = len(s) + 1
        ret = u'{0}\n{1}\n{2}\n'.format(
            Moinwiki.verbatim_open * max_subpage_lvl, text, Moinwiki.verbatim_close * max_subpage_lvl)
        return '\n' + ret + '\n'

    def open_moinpage_block_comment(self, elem):
        # text child similar to: ## some block comment
        return '\n\n' + '\n'.join(elem) + '\n\n'

    def open_moinpage_blockquote(self, elem):
        # blockquotes are generated by html_in (and maybe others), not by moinwiki_in
        # to achieve same look, we convert to bulletless unordered list
        ret = self.open_children(elem)
        ret = ret.strip()
        ret = ret.replace('\n\n', '\n\n    . ')
        ret = ret.split('<<BR>>')
        indented = []
        for line in ret:
            indented.append(u'    . ' + line)
        return '\n\n' + '\n'.join(indented) + '\n\n'

    def open_moinpage_code(self, elem):
        ret = Moinwiki.monospace
        ret += u''.join(elem.itertext())
        ret += Moinwiki.monospace
        return ret

    def open_moinpage_div(self, elem):
        childrens_output = self.open_children(elem)
        return '\n\n' + childrens_output + '\n\n'

    def open_moinpage_emphasis(self, elem):
        childrens_output = self.open_children(elem)
        return u"{0}{1}{2}".format(Moinwiki.emphasis, childrens_output, Moinwiki.emphasis)

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
        ret = Moinwiki.h * level + u' '
        ret += u''.join(elem.itertext())
        ret += u' {0}\n'.format(Moinwiki.h * level)
        return u'\n' + ret

    def open_moinpage_line_break(self, elem):
        return Moinwiki.linebreak

    def open_moinpage_list(self, elem):
        label_type = elem.get(moin_page.item_label_generate, None), elem.get(moin_page.list_style_type, None)
        self.list_item_labels.append(
            Moinwiki.list_type.get(label_type, u''))
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
        ret = u''
        if self.list_item_labels[-1] == u'' or self.list_item_labels[-1] == Moinwiki.definition_list_marker:
            self.list_item_labels[-1] = Moinwiki.definition_list_marker
            self.list_item_label = self.list_item_labels[-1] + u' '
            ret = u' ' * (len(u''.join(self.list_item_labels[:-1])) +
                          len(self.list_item_labels[:-1]))  # self.list_level
            if self.last_closed:
                ret = u'\n{0}'.format(ret)
        childrens_output = self.open_children(elem)
        return "{0}{1}{2}".format(ret, childrens_output, Moinwiki.definition_list_marker)

    def open_moinpage_list_item_body(self, elem):
        ret = u''
        if self.last_closed:
            ret = u'\n'
        ret += u' ' * (len(u''.join(self.list_item_labels[:-1])) +
                       len(self.list_item_labels[:-1])) + self.list_item_label
        return ret + self.open_children(elem)

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, u"")
        if class_:
            if class_ == "footnote":
                return u'<<FootNote({0})>>'.format(self.open_children(elem))
        return u'\n<<FootNote()>>\n'

    def open_moinpage_nowiki(self, elem):
        """{{{#!wiki ... or {{{#!highlight ... etc."""
        nowiki_marker_len, all_nowiki_args, content = elem._children
        nowiki_args = all_nowiki_args[0]
        nowiki_marker_len = int(nowiki_marker_len)
        return u'\n' + u'{' * nowiki_marker_len + u'{0}\n{1}\n'.format(nowiki_args, content) + \
               u'}' * nowiki_marker_len + u'\n'

    def include_object(self, xpointer, href):
        """
        Return a properly formatted include macro.

        xpointer similar to: u'xmlns(page=http://moinmo.in/namespaces/page) page:include(heading(my title) level(2))'
        TODO: xpointer format is ugly, Arguments class would be easier to use here.

        The include moin 2.x macro (per include.py) supports: pages (pagename), sort, items, skipitems, heading, and level.
        If incoming href == '', then there will be a pages value similar to '^^ma' that needs to be unescaped.
        TODO: some 1.9 features have been dropped.
        """
        arguments = {}
        href = href.split(':')[-1]
        args = xpointer.split('page:include(')[1][:-1]
        args = args[:-1].split(') ')
        for arg in args:
            key, val = arg.split('(')
            arguments[key] = val
        parms = ',{0},{1}'.format(arguments.get('heading', ''), arguments.get('level', ''))
        for key in ('sort', 'items', 'skipitems'):
            if key in arguments:
                parms += ',{0}="{1}"'.format(key, arguments[key])
        while parms.endswith(','):
            parms = parms[:-1]
        if not href and 'pages' in arguments:
            # xpointer needs unescaping, see comments above
            href = arguments['pages'].replace('^(', '(').replace('^)', ')').replace('^^', '^')
        return u'<<Include({0}{1})>>'.format(href, parms)

    def open_moinpage_object(self, elem):
        """
        Process objects: {{transclusions}}  and <<Include(parameters,...)>>

        Other macros are processes by open_moinpage_part.
        """
        href = elem.get(xlink.href, elem.get(xinclude.href, u''))
        if isinstance(href, Iri):
            href = unicode(href)
            href = urllib.unquote(href)

        try:
            return self.include_object(elem.attrib[xinclude.xpointer], href)
        except KeyError:
            pass

        href = href.split(u'?')
        args = u''
        if len(href) > 1:
            args = u' '.join([s for s in findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)', href[1]) if s[:3] != u'do='])
        href = href[0].split(u'wiki.local:')[-1]

        if len(elem) and isinstance(elem[0], unicode):
            # alt text for objects is enclosed within <object...>...</object>
            alt = elem[0]
        else:
            alt = elem.attrib.get(html.alt, u'')

        whitelist = {html.width: 'width', html.height: 'height', html.class_: 'class'}
        options = []
        for attr, value in elem.attrib.items():
            if attr in whitelist.keys():
                options.append('{0}="{1}"'.format(whitelist[attr], value))

        if args:
            args = u'&' + args
        if options:
            if args:
                args += u' '
            args += u' '.join(options)

        ret = u'{0}{1}|{2}|{3}{4}'.format(Moinwiki.object_open, href, alt, args, Moinwiki.object_close)
        ret = sub(r"\|+}}", "}}", ret)
        return ret

    def open_moinpage_p(self, elem):
        if moin_page.class_ in elem.attrib and 'moin-error' in elem.attrib[moin_page.class_]:
            # ignore error messages inserted into DOM
            return u''

        self.status.append("p")
        ret = u""
        if self.status[-2] == 'text':
            if self.last_closed == 'text':
                ret = Moinwiki.p * 2 + self.open_children(elem) + Moinwiki.p
            elif self.last_closed:
                ret = Moinwiki.p + self.open_children(elem) + Moinwiki.p
            else:
                ret = self.open_children(elem) + Moinwiki.p
        elif self.status[-2] == 'table':
            if self.last_closed and self.last_closed != 'table_cell' and self.last_closed != 'table_row':
                ret = Moinwiki.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        elif self.status[-2] == 'list':  # TODO: still possible? <p> after <li> removed from moinwiki_in
            if self.last_closed and (
                self.last_closed != 'list_item' and self.last_closed != 'list_item_header' and
                self.last_closed != 'list_item_footer' and self.last_closed != 'list_item_label'):
                ret = Moinwiki.linebreak + self.open_children(elem)
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
            ret = u"#!wiki"
            max_subpage_lvl = 3
            self.status.append('text')
            childrens_output = self.open_children(elem)
            self.status.pop()
            for s in findall(r'}+', childrens_output):
                if max_subpage_lvl <= len(s):
                    max_subpage_lvl = len(s) + 1
            return u'{0}{1}{2}{3}\n'.format(
                Moinwiki.verbatim_open * max_subpage_lvl,
                ret, childrens_output,
                Moinwiki.verbatim_close * max_subpage_lvl)

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

    def open_moinpage_part(self, elem):
        type = elem.get(moin_page.content_type, u"").split(u';')
        if len(type) == 2:
            if type[0] == "x-moin/macro":
                name = type[1].split(u'=')[1]
                eol = '\n\n' if elem.tag.name == 'part' else ''
                if len(elem) and elem[0].tag.name == "arguments":
                    return u"{0}<<{1}({2})>>{0}".format(
                        eol, name, elem[0][0])
                else:
                    return u"{0}<<{1}()>>{0}".format(eol, name)
            elif type[0] == "x-moin/format":
                elem_it = iter(elem)
                ret = u"{{{{{{#!{0}".format(type[1].split(u'=')[1])
                if len(elem) and elem_it.next().tag.name == "arguments":
                    args = []
                    for arg in iter(elem).next():
                        if arg.tag.name == "argument":
                            args.append(u"{0}=\"{1}\"".format(arg.get(moin_page.name, u""), u' '.join(arg.itertext())))
                    ret = u'{0}({1})'.format(ret, u' '.join(args))
                    elem = elem_it.next()
                ret = u"{0}\n{1}\n}}}}}}\n".format(ret, u' '.join(elem.itertext()))
                return ret
        return unescape(elem.get(moin_page.alt, u'')) + u"\n"

    def open_moinpage_inline_part(self, elem):
        ret = self.open_moinpage_part(elem)
        if ret[-1] == u'\n':
            ret = ret[:-1]
        return ret

    def open_moinpage_samp(self, elem):
        # text {{{more text}}} end
        ret = Moinwiki.samp_open
        ret += u''.join(elem.itertext())
        ret += Moinwiki.samp_close
        return ret

    def open_moinpage_separator(self, elem, hr_class_prefix=u'moin-hr'):
        hr_ending = u'\n'
        hr_class = elem.attrib.get(moin_page('class'))
        if hr_class:
            try:
                height = int(hr_class.split(hr_class_prefix)[1]) - 1
                if 0 <= height <= 5:
                    hr_ending = (u'-' * height) + hr_ending
            except:
                raise ElementException('page:separator has invalid class {0}'.format(hr_class))
        return Moinwiki.separator + hr_ending

    def open_moinpage_span(self, elem):
        font_size = elem.get(moin_page.font_size, u'')
        baseline_shift = elem.get(moin_page.baseline_shift, u'')
        class_ = elem.get(moin_page.class_, u'')
        if class_ == 'comment':
            return u'/* {0} */'.format(self.open_children(elem))
        if font_size:
            return u"{0}{1}{2}".format(
                Moinwiki.larger_open if font_size == u"120%" else Moinwiki.smaller_open,
                self.open_children(elem),
                Moinwiki.larger_close if font_size == u"120%" else Moinwiki.smaller_close)
        if baseline_shift == u'super':
            return u'^{0}^'.format(u''.join(elem.itertext()))
        if baseline_shift == u'sub':
            return u',,{0},,'.format(u''.join(elem.itertext()))
        return u''.join(self.open_children(elem))

    def open_moinpage_del(self, elem):  # stroke or strike-through
        return Moinwiki.stroke_open + self.open_children(elem) + Moinwiki.stroke_close

    def open_moinpage_s(self, elem):  # s is used for stroke or strike by html_in
        return self.open_moinpage_del(elem)

    def open_moinpage_ins(self, elem):  # underline
        return Moinwiki.underline + self.open_children(elem) + Moinwiki.underline

    def open_moinpage_u(self, elem):  # underline via html_in
        return self.open_moinpage_ins(elem)

    def open_moinpage_strong(self, elem):
        ret = Moinwiki.strong
        return u"{0}{1}{2}".format(Moinwiki.strong, self.open_children(elem), Moinwiki.strong)

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get(moin_page.class_, u'')
        # moin-wiki-table class was added by moinwiki_in so html_out can convert multiple body's into head, foot
        self.table_tableclass = self.table_tableclass.replace(u'moin-wiki-table', u'').strip()
        self.table_tablestyle = elem.attrib.get(moin_page.style, u'')
        if elem[0].tag == moin_page.caption:
            self.table_caption = elem[0][0]
        else:
            self.table_caption = u''
        self.table_rowsstyle = u''
        self.table_rowsclass = u''
        self.table_multi_body = u''
        self.status.append('table')
        self.last_closed = None
        ret = self.open_children(elem)
        self.status.pop()
        return u'\n' + ret + u'\n'

    def open_moinpage_caption(self, elem):
        # return empty string, text has already been processed in open_moinpage_table above
        return u''

    def open_moinpage_table_header(self, elem):
        # used for ReST to moinwiki conversion, maybe others that generate table head
        ret = self.open_children(elem)
        return ret + u'=====\n'

    def open_moinpage_table_footer(self, elem):
        # no known use, need some markup that generates table foot
        ret = self.open_children(elem)
        return u'=====\n' + ret

    def open_moinpage_table_body(self, elem):
        self.table_rowsclass = ''
        ret = self.table_multi_body + self.open_children(elem)
        # multible body elements separate header/body/footer within DOM created by moinwiki_in
        self.table_multi_body = u'=====\n'
        return ret

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get(moin_page.class_, u'')
        self.table_rowclass = u' '.join([s for s in [self.table_rowsclass, self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get(moin_page.style, u'')
        self.table_rowstyle = u' '.join([s for s in [self.table_rowsstyle, self.table_rowstyle] if s])
        ret = self.open_children(elem)
        self.table_rowstyle = u''
        self.table_rowclass = u''
        return ret + Moinwiki.table_marker + u'\n'

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get(moin_page.class_, u'')
        table_cellstyle = elem.attrib.get(moin_page.style, u'')
        number_columns_spanned = int(elem.get(moin_page.number_columns_spanned, 1))
        number_rows_spanned = elem.get(moin_page.number_rows_spanned, None)
        ret = Moinwiki.table_marker
        attrib = []

        # TODO: maybe this can be written shorter
        if self.table_tableclass:
            attrib.append(u'tableclass="{0}"'.format(self.table_tableclass))
            self.table_tableclass = u''
        if self.table_tablestyle:
            attrib.append(u'tablestyle="{0}"'.format(self.table_tablestyle))
            self.table_tablestyle = u''
        if self.table_caption:
            attrib.append(u'caption="{0}"'.format(self.table_caption))
            self.table_caption = u''
        if self.table_rowclass:
            attrib.append(u'rowclass="{0}"'.format(self.table_rowclass))
            self.table_rowclass = u''
        if self.table_rowstyle:
            attrib.append(u'rowstyle="{0}"'.format(self.table_rowstyle))
            self.table_rowstyle = u''
        if table_cellclass:
            attrib.append(u'class="{0}"'.format(table_cellclass))
        if table_cellstyle:
            attrib.append(u'style="{0}"'.format(table_cellstyle))
        if number_rows_spanned:
            attrib.append(u'rowspan="{0}"'.format(number_rows_spanned))
        if number_columns_spanned > 1:
            attrib.append(u'colspan="{0}"'.format(number_columns_spanned))

        attrib = u' '.join(attrib)

        if attrib:
            ret += u'<{0}>'.format(attrib)
        childrens_output = self.open_children(elem)
        return ret + childrens_output

    def open_moinpage_table_of_content(self, elem):
        return u"<<TableOfContents({0})>>\n".format(elem.get(moin_page.outline_level, u""))

    def open_xinclude(self, elem):
        """Processing of transclusions is similar to objects."""
        return self.open_moinpage_object(elem)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document, type_moin_wiki
default_registry.register(Converter.factory, type_moin_document, type_moin_wiki)
default_registry.register(Converter.factory, type_moin_document, Type('x-moin/format;name=wiki'))
