General
=======
- verify if these TODO items are still valid
- move valid TODO items either to the respective code file or to the issue
  tracker (on bitbucket.org) and remove them from here


DOM Converters
==============

General
-------

If someone adds a new type of node in the Moinmoin DOM tree:
  
  TODO: add support of new types of node

Allow creation of unicode URIs for wiki links. This should also provide
access to the query parameters.

Support for per-instance converters.

Include converter
-----------------
- Handle URIs using the Uri class.

Macro converter
---------------
- Move macro definitions into different namespace.
- Footnote placing.

HTML output converter
---------------------
- Footnote placing.

ReStructuredText
----------------

Some syntax of ReStructuredText is ignored because it can't be converted to
the current DOM tree (like inline style/class/template replacement via directives).
Moin needs some page about unsupported things or changes in DOM tree.

Mediawiki
---------

Mediawiki->DOM converter based on moinwiki->DOM parsing model. Moinwiki parser
has blocks (multiline markup) and inline markup, but Mediawiki has tags that are
inline and can be extended to next lines (until closing tag or end of the file).
This creates a problem, for some tags it can be solved by implemented
preprocessor, but it doesn't work with tags that have multiline output
(like <blockquote>).

There are two ways to fix it:

- preprocessor must input '\n' before <blockquote> and after </blockquote>
- parser must be able to start new block(multiline) element after inline lexem.


Item
====
- Support different output types again.

- Converter-aware quickhelp.
  Possibilities:
  - Use help from converter $type -> application/x-moin-document.
  - Use a different converter $type -> application/x-moin-document;quickhelp
    which always returns the help.
  - Use another registry for the quickhelps within the converter framework.

- Fix GUI editor.
  - Don't expand macros and links(?) in HTML.
  - Replace html -> moin wiki converter.


Macros
======

Macro handling
--------------
- Handle errors.
- Merge Macros and Converters

Include macro
-------------
- Argument parsing.
  The argument parsing through wikiutil.invoke_extension_method is currently
  incompatible with several examples of the macro usage.
- Normalization of heading levels - e.g. if the tree has h1->h2->h4 (h3 is
  missing). For simple pages, we could just ignore this problem and require
  correct heading levels in input markup. But if you use Include much, this
  can get either a pain (esp. if you change levels) or even impossible (if
  same content is included on different pages into different levels).
  Would also fix broken looking TOC if levels are missing.
  Currently, the code has only 1 normalization: that the biggest heading
  on a rendered page starts at h1.
- For generation of a single output document (that can be either used as a
  single html file or transformed to a PDF), page links need to be changed:
  Usually page links just link to another page url. But if one assembles one
  large document using Include, one wants the links to the pages that got
  included point to some anchor where the page inclusion starts. For normal
  anchor links to / within included pages, it should be #Pagename-anchorid.

