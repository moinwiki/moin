# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - reStructuredText markup output converter

Converts an internal document tree into reStructuredText markup.

This converter based on ReStructuredText 2006-09-22.
"""


from __future__ import absolute_import, division

from MoinMoin.util.tree import moin_page, xlink

from emeraldtree import ElementTree as ET

import re

from werkzeug.utils import unescape


class Cell(object):

    def __init__(self, text):
        self.text = text

    def __call__(self):
        return self.text

    def height(self):
        return len(self.text.split('\n'))

    def width(self):
        max = 0
        for i in self.text.split('\n'):
            if len(i) > max:
                max = len(i)
        return max


class Table(object):
    """
    An object of this class collects the structure of a table
    and represent it in ReStructuredText syntax.
    """

    def __init__(self):
        self.i = -1
        self.j = -1
        self.table = []
        self.header_count = 0
        self.rowclass = ''

    def add_row(self):
        """
        Add new row to the table.
        """
        if self.rowclass == 'table-header':
            self.header_count += 1
        row = []
        self.i += 1
        self.j = 0
        self.table.append(row)
        if self.i > 0:
            if len(self.table[-2]) > (self.j):
                self.add_cell(self.table[-2][self.j][0],
                                self.table[-2][self.j][1] - 1, Cell(''))
        return row

    def end_row(self):
        """
        Adds empyt cells to current row if it's too short.

        Moves the row to the head of the table if it is table header.
        """
        if len(self.table) > 1:
            if len(self.table[-2]) > len(self.table[-1]):
                self.add_cell(1, 1, Cell(''))
                self.end_row()
            if self.rowclass == 'table-header':
                self.table.insert(self.header_count - 1, self.table.pop())

    def add_cell(self, cs, rs, cell):
        """
        Adds cell to the row.

        :param cs: number of columns spanned
        """
        if cs < 1 or rs < 1:
            return
        self.table[-1].append((cs, rs, cell))
        for i in range(cs-1):
            self.table[-1].append((cs-i-1, rs, Cell('')))
        self.j += cs
        if self.i > 0:
            if len(self.table[-2]) > self.j:
                self.add_cell(self.table[-2][self.j][0],
                                self.table[-2][self.j][1] - 1, Cell(''))
        return

    def height(self):
        """
        :returns: number of rows in the table
        """
        return len(self.table)

    def width(self):
        """
        :returns: width of rows in the table or zero if rows have different width
        """
        if not self.table:
            return 0
        width = len(self.table[0])
        for row in self.table:
            if len(row) != width:
                return 0
        return width

    def col_width(self, col):
        """
        Counts the width of the column in ReSturcturedText representation.

        :param col: index of the column
        :returns: number of characters
        """
        if self.width() <= col:
            return 0
        width = 0
        for row in self.table:
            if row[col][2].width() > width:
                width = row[col][2].width()
        return width

    def row_height(self, row):
        """
        Counts lines in ReSturcturedText representation of the row

        :param row: index of the row
        :returns: number of lines
        """
        if self.height() <= row:
            return 0
        height = 0
        for col in self.table[row]:
            if col[2].height() > height:
                height = col[2].height()
        return height

    def __repr__(self):
        """
        Represent table using ReStructuredText syntax.
        """
        ret = []
        if self.height() and self.width():
            cols = []
            rows = []
            row = self.table[0]
            for col in range(self.width()):
                cols.append(self.col_width(col))
            for row in range(self.height()):
                rows.append(self.row_height(row))
            ret = []
            line = [u'+']
            row = self.table[0]
            for col in range(len(cols)):
                line.append(u'-'*cols[col])
                if self.table[0][col][0] > 1:
                    line.append(u'-')
                else:
                    line.append(u'+')
            ret.append(''.join(line))
            for row in range(len(rows)):
                for i in range(rows[row]):
                    line = []
                    line.append(u'|')
                    for col in range(len(cols)):
                        if self.table[row][col][2].height() <= i:
                            line.append(''.ljust(cols[col])[:cols[col]])
                        else:
                            line.append(
                                self.table[row][col][2]().split(
                                    u'\n')[i].ljust(cols[col])[:cols[col]])
                        if self.table[row][col][0] > 1:
                            line.append(' ')
                        else:
                            line.append(u'|')

                    ret.append(''.join(line))
                line = [u'+']
                for col in range(len(cols)):
                    if self.table[row][col][1] > 1:
                        line.append(' '*cols[col])
                    elif row == self.header_count - 1:
                        line.append(u'='*cols[col])
                    else:
                        line.append(u'-'*cols[col])
                    if self.table[row][col][0] > 1:
                        if row + 1 < len(rows)\
                                and self.table[row + 1][col][0] > 1\
                                or row + 1 >= len(rows):
                            line.append(u'-')
                        else:
                            line.append(u'+')
                    else:
                        line.append(u'+')
                ret.append(''.join(line))
        return u'\n'.join(ret)


class ReST(object):
    """
    ReST syntax elements
    It's dummy
    """
    h = u"""= - ` : ' " ~ ^ _ * + # < >""".split()
    a_separator = u'|'
    verbatim = u'::'
    monospace = u'``'
    strong = u"**"
    emphasis = u"*"
    p = u'\n'
    linebreak = u'\n\n'
    separator = u'----'
    list_type = {
        (u'definition', None): u'',
        (u'ordered', None): u'1.',
        (u'ordered', u'lower-alpha'): u'a.',
        (u'ordered', u'upper-alpha'): u'A.',
        (u'ordered', u'lower-roman'): u'i.',
        (u'ordered', u'upper-roman'): u'I.',
        (u'unordered', None): u'*',
        (None, None): u' ',
        }


class Converter(object):
    """
    Converter application/x.moin.document -> text/x.moin.rst
    """
    namespaces = {
        moin_page.namespace: 'moinpage'}

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
                'p',
                'page',
                'separator',
                'span',
                'strong',
                'object',
                'table',
                'table_header',
                'teble_footer',
                'table_body',
                'table_row',
                'table_cell')}

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

        self.list_item_labels = []
        self.list_item_label = u''
        self.list_level = -1

        # 'text' - default status - <p> = '/n' and </p> = '/n'
        # 'table' - text inside table - <p> = '<<BR>>' and </p> = ''
        # 'list' - text inside list -
        #       <p> if after </p> = '<<BR>>' and </p> = ''
        # status added because of
        #  differences in interpretation of <p> in different places
    def __call__(self, root):
        self.status = ['text', ]
        self.last_closed = None
        self.list_item_label = []
        self.footnotes = []
        self.objects = []
        self.all_used_references = []
        self.anonymous_reference = None
        self.used_references = []
        self.delete_newlines = False
        ret = self.open(root)
        notes = u"\n\n".join(u".. [#] {0}".format(note.replace(u"\n", u"\n  ")) for note in self.footnotes)
        if notes:
            return ret + self.define_references() + u"\n\n{0}\n\n".format(notes)

        return ret + self.define_references()

    def open_children(self, elem):
        childrens_output = []
        self.delete_newlines = False
        delete_newlines = False
        for child in elem:
            if isinstance(child, ET.Element):
                childs_output = self.open(child)
                if self.delete_newlines:
                    while childrens_output and re.match(r'(\n*)\Z', childrens_output[-1]):
                        childrens_output.pop()
                    if childrens_output:
                        last_newlines = r'(\n*)\Z'
                        i = -len(re.search(last_newlines, childrens_output[-1]).groups(1)[0])
                        if i:
                            childrens_output[-1] = childrens_output[-1][:i]
                    else:
                        delete_newlines = True
                self.delete_newlines = False
                childrens_output.append(childs_output)
            else:
                if self.status[-1] == "table":
                    if self.last_closed == "p":
                        childrens_output.append(u'\n\n')
                elif self.status[-1] == "list":
                    child =\
                        re.sub(r"\n(.)", lambda m: u"\n{0}{1}".format(u' '*(len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)), child)
                    if self.last_closed == "p":
                        childrens_output.append(u'\n'
                                + u' '
                                * (len(''.join(self.list_item_labels))
                                   + len(self.list_item_labels)))
                elif self.status[-1] == "text":
                    if self.last_closed == "p":
                        childrens_output.append(self.define_references())
                        childrens_output.append(u'\n')
                elif self.status[-2] == "list":
                    child =\
                        re.sub(r"\n(.)", lambda m: u"\n{0}{1}".format(u' '*(len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)), child)
                childrens_output.append(child)
                self.last_closed = 'text'
        self.delete_newlines = delete_newlines
        return u''.join(childrens_output)

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'open_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
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
        text = u''.join(elem.itertext()).replace(u'\n', u' ')
        # TODO: check that links have different alt texts
        if text in [t for (t, h) in self.all_used_references]:
            if (text, href) in self.all_used_references:
                return u"`{0}`_".format(text)
            if not self.anonymous_reference:
                self.anonymous_reference = href
                self.used_references.insert(0, (u"_", href))
                return u"`{0}`__".format(text)
            else:
                while text in [t for (t, h) in self.all_used_references]:
                    text = text + u"~"
        self.used_references.append((text, href))
        self.all_used_references.append((text, href))
        #self.objects.append("\n\n.. _%s: %s\n\n" % (text, href))
        return u"`{0}`_".format(text)

    def open_moinpage_blockcode(self, elem):
        text = u''.join(elem.itertext())
        max_subpage_lvl = 3
        text = text.replace(u'\n', u'\n  '
                                  + u' ' * (len(u''.join(self.list_item_labels))
                                         + len(self.list_item_labels)))

        if self.list_level >= 0:
            self.delete_newlines = True
            """
            while self.output and re.match(r'(\n*)\Z', self.output[-1]):
                self.output.pop()
            last_newlines = r'(\n*)\Z'
            if self.output:
                i = -len(re.search(last_newlines, self.output[-1]).groups(1)[0])
                if i:
                    self.output[-1] = self.output[-1][:i]
            """
        return u"::\n\n  {0}{1}\n\n".format(u' ' * (len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), text)

    def open_moinpage_code(self, elem):
        ret = u"{0}{1}{2}".format(ReST.monospace, u''.join(elem.itertext()), ReST.monospace)
        return ret

    def open_moinpage_emphasis(self, elem):
        childrens_output = self.open_children(elem)
        return u"{0}{1}{2}".format(ReST.emphasis, childrens_output, ReST.emphasis)

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        text = u''.join(elem.itertext())
        try:
            level = int(level)
        except ValueError:
            raise ElementException(u'page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = u"\n\n{0}\n{1}\n{2}\n\n".format(ReST.h[level] * len(text), text, ReST.h[level] * len(text))
        return ret

    def open_moinpage_line_break(self, elem):
        if self.status[-1] == "list":
            return (ReST.linebreak
                    + u' '
                      * (len(u''.join(self.list_item_labels))
                         + len(self.list_item_labels)))
        if self.last_closed == 'p':
            return u'\n\n'
        return ReST.linebreak

    def open_moinpage_list(self, elem):
        label_type = (elem.get(moin_page.item_label_generate, None),
                        elem.get(moin_page.list_style_type, None))
        self.list_item_labels.append(
            ReST.list_type.get(label_type, u' '))
        self.list_level += 1
        ret = u''
        if self.status[-1] == 'text' and self.last_closed:
            ret = u'\n\n'
        elif self.status[-1] != 'text' or self.last_closed:
            ret = u'\n'
        self.status.append('list')
        self.last_closed = None
        ret += self.open_children(elem)
        self.list_item_labels.pop()
        self.list_level -= 1
        self.status.pop()
        if self.status[-1] == 'list':
            return ret + u''
        return ret + u'\n'

    def open_moinpage_list_item(self, elem):
        self.list_item_label = self.list_item_labels[-1] + u' '
        return self.open_children(elem)

    def open_moinpage_list_item_label(self, elem):
        ret = u''
        if self.list_item_labels[-1] == u'' or self.list_item_labels[-1] == u' ':
            self.list_item_labels[-1] = u' '
            self.list_item_label = self.list_item_labels[-1] + u' '
            ret = (u' '
                   * (len(u''.join(self.list_item_labels[:-1]))
                      + len(self.list_item_labels[:-1])))
            if self.last_closed and self.last_closed != 'list':
                ret = u'\n{0}'.format(ret)
            return ret + self.open_children(elem)
        return self.open_children(elem)

    def open_moinpage_list_item_body(self, elem):
        ret = u''
        if self.last_closed:
            ret = u'\n'
        ret += (u' ' * (len(u''.join(self.list_item_labels[:-1]))
                       + len(self.list_item_labels[:-1]))
                + self.list_item_label)
        if self.list_item_labels[-1] in [u'1.', u'i.', u'I.', u'a.', u'A.']:
            self.list_item_labels[-1] = u'#.'

        ret = self.define_references() + ret + self.open_children(elem)
        if self.last_closed == "text":
            return ret + u'\n'
        return ret

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, u"")
        if class_:
            self.status.append('list')
            if class_ == u"footnote":
                self.footnotes.append(self.open_children(elem))
            self.status.pop()
        return u' [#]_ '

    def open_moinpage_object(self, elem):
        # TODO: object parameters support
        href = elem.get(xlink.href, u'')
        href = href.split(u'?')
        args = u''
        if len(href) > 1:
            args =[s for s in re.findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)',
                                            href[1]) if s[:3] != u'do=']
        href = href[0]
        alt = elem.get(moin_page.alt, u'')
        if not alt:
            ret = u''
        else:
            ret = u'|{0}|'.format(alt)
        args_text = u''
        if args:
            args_text = u"\n  {0}".format(u'\n  '.join(u':{0}: {1}'.format(arg.split(u'=')[0], arg.split(u'=')[1]) for arg in args))
        self.objects.append(u".. {0} image:: {1}{2}".format(ret, href, args_text))
        return ret

    def open_moinpage_p(self, elem):
        ret = u''
        if self.status[-1] == 'text':
            self.status.append('p')
            set = self.define_references()
            if self.last_closed == 'text':
                ret = ReST.p * 2 + self.open_children(elem) + ReST.p + set
            elif self.last_closed:
                ret = ReST.p + self.open_children(elem) + ReST.p + set
            else:
                ret = self.open_children(elem) + ReST.p + set
        elif self.status[-1] == 'table':
            self.status.append('p')
            if self.last_closed and self.last_closed != 'table_cell'\
                                and self.last_closed != 'table_row'\
                                and self.last_closed != 'table_header'\
                                and self.last_closed != 'table_footer'\
                                and self.last_closed != 'table_body'\
                                and self.last_closed != 'line_break':
          #                      and self.last_closed != 'p':
                ret = ReST.linebreak + self.open_children(elem)
            elif self.last_closed == 'p' or self.last_closed == 'line_break':
                ret = self.open_children(elem)
            else:
                ret = self.open_children(elem)
        elif self.status[-1] == 'list':
            self.status.append('p')
            if self.last_closed and self.last_closed == 'list_item_label':
                ret = self.open_children(elem)
            elif self.last_closed and self.last_closed != 'list_item'\
                                and self.last_closed != 'list_item_header'\
                                and self.last_closed != 'list_item_footer'\
                                and self.last_closed != 'p':
                ret = (ReST.linebreak + u' '
                                        * (len(u''.join(self.list_item_labels))
                                           + len(self.list_item_labels)) + self.open_children(elem))
            elif self.last_closed and self.last_closed == 'p':
                #return ReST.p +\
                ret = (u"\n" + u' ' * (len(u''.join(self.list_item_labels))
                                    + len(self.list_item_labels)) + self.open_children(elem))
            else:
                ret = self.open_children(elem)
            if not self.delete_newlines:
                ret +=  u"\n"
        else:
            self.status.append('p')
            ret = self.open_children(elem)
        self.status.pop()
        return ret

    def open_moinpage_page(self, elem):
        self.last_closed = None
        return self.open_children(elem)

    def open_moinpage_body(self, elem):
        return self.open_children(elem)

    def open_moinpage_part(self, elem):
        type = elem.get(moin_page.content_type, u"").split(u';')
        if len(type) == 2:
            if type[0] == u"x-moin/macro":
                if len(elem) and iter(elem).next().tag.name == "arguments":
                    alt = u"<<{0}({1})>>".format(type[1].split(u'=')[1], u','.join([u''.join(c.itertext()) for c in iter(elem).next() if c.tag.name == "argument"]))
                else:
                    alt = u"<<{0}()>>".format(type[1].split(u'=')[1])

                obj = u".. |{0}| macro:: {1}".format(alt, alt)
                self.objects.append(obj)
                return u" |{0}| ".format(alt)
            elif type[0] == u"x-moin/format":
                elem_it = iter(elem)
                ret = u"\n\n.. parser:{0}".format(type[1].split(u'=')[1])
                if len(elem) and elem_it.next().tag.name == "arguments":
                    args = []
                    for arg in iter(elem).next():
                        if arg.tag.name == "argument":
                            args.append(u"{0}=\"{1}\"".format(arg.get(moin_page.name, u""), u' '.join(arg.itertext())))
                    ret = u'{0} {1}'.format(ret, u' '.join(args))
                    elem = elem_it.next()
                ret = u"{0}\n  {1}".format(ret, u' '.join(elem.itertext()))
                return ret
        return elem.get(moin_page.alt, u'') + u"\n"

    def open_moinpage_inline_part(self, elem):
        return self.open_moinpage_part(elem)

    def open_moinpage_separator(self, elem):
        return u'\n\n' + ReST.separator + u'\n\n'

    def open_moinpage_span(self, elem):
        baseline_shift = elem.get(moin_page.baseline_shift, u'')

        # No text decoration and text size in rst, this can be deleted
        """
        text_decoration = elem.get(moin_page.text_decoration, u'')
        font_size = elem.get(moin_page.font_size, u'')
        if text_decoration == 'line-through':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return ''
        if text_decoration == 'underline':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return ''
        if font_size:
            self.children.append(iter(elem))
            self.opened.append(elem)
            return ''
        """
        if baseline_shift == 'super':
            return u"\\ :sup:`{0}`\\ ".format(u''.join(elem.itertext()))
        if baseline_shift == 'sub':
            return u"\\ :sub:`{0}`\\ ".format(u''.join(elem.itertext()))
        return self.open_children(elem)

    def open_moinpage_strong(self, elem):
        return ReST.strong + self.open_children(elem) + ReST.strong

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get('class', u'')
        self.table_tablestyle = elem.attrib.get('style', u'')
        self.table_rowsstyle = u''
        self.table_rowsclass = u''
        self.status.append('table')
        self.last_closed = None
        self.table = []
        self.tablec = Table()
        self.open_children(elem)
        self.status.pop()
        table = repr(self.tablec)
        if self.status[-1] == "list":
            table =\
                re.sub(r"\n(.)", lambda m: u"\n{0}{1}".format(u' '*(len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)), u"\n" + table)
            return table + ReST.p
        return table + ReST.linebreak

    def open_moinpage_table_header(self, elem):
        # is this correct rowclass?
        self.tablec.rowclass = 'table-header'
        return self.open_children(elem)

    # No table footer support, TODO if needed
    """
    def open_moinpage_table_footer(self, elem):
        self.tablec.rowclass = 'table-footer'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_footer(self, elem):
        self.table_rowsclass = ''
        return ''
    """

    def open_moinpage_table_body(self, elem):
        self.tablec.rowclass = 'table-body'
        return self.open_children(elem)

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get('class', u'')
        self.table_rowclass = u' '.join([s for s in [self.table_rowsclass,
                                                    self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get('style', u'')
        self.table_rowstyle = u' '.join([s for s in [self.table_rowsstyle,
                                                    self.table_rowstyle] if s])
        self.table.append([])
        self.tablec.add_row()
        ret = self.open_children(elem)
        self.table_rowstyle = ''
        self.table_rowclass = ''
        self.tablec.end_row()
        return ret

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get('class', u'')
        table_cellstyle = elem.attrib.get('style', u'')
        number_cols_spanned\
                = int(elem.get(moin_page.number_cols_spanned, 1))
        number_rows_spanned\
                = int(elem.get(moin_page.number_rows_spanned, 1))

        attrib = []

        # TODO: styles and classes
        """
        if self.table_tableclass:
            attrib.append('tableclass="{0}"'.format(self.table_tableclass))
            self.table_tableclass = ''
        if self.table_tablestyle:
            attrib.append('tablestyle="{0}"'.format(self.table_tablestyle))
            self.table_tableclass = ''
        if self.table_rowclass:
            attrib.append('rowclass="{0}"'.format(self.table_rowclass))
            self.table_rowclass = ''
        if self.table_rowstyle:
            attrib.append('rowclass="{0}"'.format(self.table_rowstyle))
            self.table_rowstyle = ''
        if table_cellclass:
            attrib.append('class="{0}"'.format(table_cellclass))
        if table_cellstyle:
            attrib.append('style="{0}"'.format(table_cellstyle))
        if number_rows_spanned:
            attrib.append('|'+str(number_rows_spanned))

        attrib = ' '.join(attrib)
        """
        self.table[-1].append((number_cols_spanned,
                                number_rows_spanned,
                                [self.open_children(elem)]))
        cell = self.table[-1][-1]
        self.tablec.add_cell(cell[0], cell[1], Cell(u''.join(cell[2])))
        return u''

    def open_moinpage_table_of_content(self, elem):
        depth = elem.get(moin_page.outline_level, u"")
        ret = u"\n\n.. contents::"
        if depth:
            ret += u"\n   :depth: {0}".format(depth)
        return ret + u"\n\n"

    def define_references(self):
        """
        Adds defenitions of founded links and objects to the converter output.
        """
        ret = u''
        self.all_used_references.extend(self.used_references)
        definitions = [u" " * (len(u''.join(self.list_item_labels))
                                    + len(self.list_item_labels))
                                  + u".. _{0}: {1}".format(t, h) for t, h in self.used_references]
        definitions.extend(u" " * (len(u''.join(self.list_item_labels))
                                     + len(self.list_item_labels))
                                  + link for link in self.objects)
        definition_block = u"\n\n".join(definitions)

        if definitions:
            if self.last_closed == 'list_item_label':
                ret += u"\n{0}\n\n".format(definition_block)
            else:
                ret += u"\n\n{0}\n\n".format(definition_block)

        self.used_references = []
        self.objects = []
        self.anonymous_reference = None
        return ret


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter.factory,
                          type_moin_document,
                          Type('text/x-rst'))
default_registry.register(Converter.factory,
                          type_moin_document,
                          Type('x-moin/format;name=rst'))

