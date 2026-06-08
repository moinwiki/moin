.. _moinpage-dom:

===================================
  The internal MoinPage DOM
===================================

At the core of Moin's document conversion is an "EmeraldTree_" based
internal document format, the `MoinPage` DOM tree.

Unfortunately, the MoinPage format is only sparsely documented, with
hints in `<../../src/moin/utils/tree.py>`__ and docstrings and comments
in the converter modules in `<../../src/moin/converters/>`__.
Also the unit tests in `<../../src/moin/converters/>`__ reveal some
insights.

This document is an attempt to improve the situation.
Please help by revising and adding information and insights.

Elements
********

As the main target format is HTML, the most complete and up to date
authority on MoinPage elements and their attributes is the source of the
HTML-Out converter `<../../src/moin/converters/html_out.py>`__.

Most MoinPage elements are equivalent to HTML elements.

Some share also the name:

  <a>, <aside>, <audio>, <blockquote>, <code>, <del>, <div>, <figure>,
  <figcaption>, <ins>, <kbd>, <object>, <p>, <s>, <samp>, <span>,
  <strong>, <sub>, <sup>, <table>, <u>, <video>

Others have a more descriptive name (mostly inspired by DocBook_):

  <blockcode>, <block_comment>, <emphasis>, <line_break>, <quote>,
  <separator>, <table_body>, <table_cell>, <table_cell_head>,
  <table_footer>, <table_header>, <table_row>

Additional elements represent features present in several input formats
but missing in HTML (mainly inspired by DocBook_ or Docutils_)

  <admonition>, <note>, <noteref>, <nowiki>, <line_block_line>,
  <line_block>, <literal>, <page>, <table_of_content>

At some stages, the representation in MoinPage differs from HTML:

* A single heading element <h level=N> replaces HTML's <h1>, …, <h6>.
* The various list types are represented by <list> <list_item>,
  <list_item_label>, <list_item_body> using a set of specific attributes.

The "macro" feature uses the special auxiliary elements <part> and
<inline_part>.


Namespaces
**********

Almost all elements and many of their attributes use the `moin-page`
namespace.

However, elements and attributes may use "foreign" namespaces to
"inherit" definitions from external specifications or to prevent naming
collisions.

* `xinclude` is used for transclusions (<include> element and some
  of its attributes).

* `xlink` is used for link-related attributes (similar to DocBook_).

* `xml` is used for the "id", "lang", and "base" attributes (similar to
  DocBook_) by ``docbook_in``, ``html_in``, and ``markdown_in`` while
  ``mediawiki_in``, ``moinwiki_in`` and ``rst_in`` use "moinpage:id".
  ``html_out`` supports both, "xml:id" and "moinpage:id".

  TODO: consistently use "xml:id"?

  It may be related to the question `xml:lang` vs. `moinpage:lang`.
  According to
  https://www.w3.org/International/questions/qa-when-xmllang.en.html#answer,
  one should use `xml:lang` to describe the (natural) language of the
  document or a part of it and an own element or attribute (like
  `moinpage:lang`) for a value describing an external source (like
  languages supported by a program). Therefore, DocBook deprecated the
  "language" attribute in favour of "xml:lang".


Converters may use "foreign" namespaces on moin DOM elements to attach
additional information for round-trips or for the HTML rendering.


* `html` is used for the "data-lines" attribute added by Moin.
  `html` is also used by various ``…-in`` converters for attributes defined
  in the HTML standard ("alt", "class", "style", "href", ...).


Representation of inline text that is some literal value
********************************************************

In addition to a generic "literal text" markup, MoinPage supports three,
more specific "monospace-styled" elements:

=========  ===========  ============  ===========  ================
..         generic      source code   user input   computer output
=========  ===========  ============  ===========  ================
MoinPage   <literal>    <code>        <kbd>        <samp>

DocBook    <literal>    <code>        <userinput>  <computeroutput>

HTML       <tt> [#tt]_  <code>        <kbd>        <samp>

MediaWiki  <tt> [#tt]_  <code>        <kbd>        <samp>

Markdown   <tt> [#tt]_  \`…`          <kbd>        <samp>

MoinWiki   \`…`          {{{…}}}       n/a          n/a

rST        \``…``        \:code:\`…`   \:kbd:\`…`   \:samp:\`…`

Creole     {{{ … }}}    n/a           n/a          n/a
=========  ===========  ============  ===========  ================

.. [#tt] The HTML tag <tt> is deprecated.
   Moin recognizes <tt> but writes <span class="monospaced">.
   A rule in ``common.css`` sets the content in a monospaced font.

.. References
   ----------

.. _DocBook: https://tdg.docbook.org/tdg/5.1/
.. _EmeraldTree: https://github.com/moinwiki/emeraldtree
.. _Docutils: https://docutils.sourceforge.io/
