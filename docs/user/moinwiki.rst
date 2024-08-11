.. role:: underline
.. role:: strikethrough
.. role:: sup
.. role:: sub
.. role:: bolditalic
.. role:: smaller
.. role:: larger


==========================
Moin Wiki markup overview
==========================

This document describes the features of the moinwiki markup language.
Because this document was created using  Restructured Text, which
does not support some of the features available in moinwiki, the
examples below may show both the markup and result as block or
predefined code.

Features currently not working with moin's Wiki parser are marked
with **MOINTODO**.

Table Of Contents
=================

Table of contents:

``<<TableOfContents()>>``

Table of contents (up to 2nd level headings only):

``<<TableOfContents(2)>>``

Headings
========

**Markup**: ::

 = Level 1 =
 == Level 2 ==
 === Level 3 ===
 ==== Level 4 ====
 ===== Level 5 =====
 ====== Level 6 ======

**Result**:

Level 1
=======

**Intentionally not rendered as level 1 so as to not interfere with Sphinx's indexing**

Level 2
=======

Level 3
-------

Level 4
*******

Level 5
:::::::

Level 6
+++++++

**Notes**:
 - Closing equals signs are compulsory.
 - Also, whitespace between the first word of the heading and the
   opening equals sign will not be shown in the output (ie. leading
   whitespace is stripped).

Text formatting
===============

The following is a table of inline markup that can be used to control text
formatting in Moin.

+-------------------------------------+---------------------------------------+
| Markup                              | Result                                |
+=====================================+=======================================+
| ``'''Bold Text'''``                 | **Bold text**                         |
+-------------------------------------+---------------------------------------+
| ``''Italic''``                      | *Italic*                              |
+-------------------------------------+---------------------------------------+
| ``'''''Bold Italic'''''``           | :bolditalic:`Bold Italic`             |
+-------------------------------------+---------------------------------------+
| ```Monospace```                     | ``Monospace``                         |
+-------------------------------------+---------------------------------------+
| ``{{{Code}}}``                      | ``Code``                              |
+-------------------------------------+---------------------------------------+
| ``__Underline__``                   | :underline:`Underline`                |
+-------------------------------------+---------------------------------------+
| ``^Super^Script``                   | :sup:`Super` Script                   |
+-------------------------------------+---------------------------------------+
| ``,,Sub,,Script``                   | :sub:`Sub` Script                     |
+-------------------------------------+---------------------------------------+
| ``~-Smaller-~``                     | :smaller:`Smaller`                    |
+-------------------------------------+---------------------------------------+
| ``~+Larger+~``                      | :larger:`Larger`                      |
+-------------------------------------+---------------------------------------+
| ``--(Stroke)--``                    | :strikethrough:`Stroke`               |
+-------------------------------------+---------------------------------------+

Hyperlinks
==========

Moin2 hyperlinks are enclosed within double brackets. There are three possible
fields separated by "|" characters: ::

  1. PageName, relative URL, fully qualified URL, or interwiki link
  2. Text description or transcluded icon: [[ItemName|{{MyLogo.png}}]]
  3. Parameters: target, title, download, class, and accesskey are supported

The special CSS class `redirect` may be used to immediately redirect the browser
to an internal or external page. Once placed inside an item,
that item cannot be viewed as redirection is immediate. To edit the item,
type .../+modify/ItemName in the browsers address bar.

Examples with parameters are not shown below because the effect cannot be
duplicated with reST markup. To open a link in a new tab or window with a
mouseover title, do: ::

  * [[ItemName|my favorite item|target=_blank,title="Go There!"]]

Internal Links
--------------

Internal links for namespaces work the same as an item in the default namespace with subitems.
Links without a leading `/` or `../` refer to an item in the top level of the default namespace,
even if the current item is not in the default namespace.
Links with a leading `/` refer to a subitem of the current item. Links with a leading `../`
refer to a sibling of the current item.

+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| Markup                                    | Result                                      | Comments                                    |
+===========================================+=============================================+=============================================+
| ``[[ItemName]]``                          | `ItemName <ItemName>`_                      | Link to an item                             |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[ItemName|Named Item]]``               | `Named Item <ItemName>`_                    | Named link to an internal item              |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[#AnchorName]]``                       | `#AnchorName <#AnchorName>`_                | Link to an anchor in the current item       |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[#AnchorName|AnchorName]]``            | `AnchorName <#AnchorName>`_                 | Link to a named anchor                      |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[ItemName#AnchorName]]``               | `ItemName#AnchorName <ItemName#AnchorName>`_| Link to an anchor in an internal item       |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[ItemName#AnchorName|Named Item1]]``   | `Named Item1 <ItemName#AnchorName>`_        | Named link to an anchor in an internal item |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[../SiblingItem]]``                    | `../SiblingItem <../SiblingItem>`_          | Link to a sibling of the current item       |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[/SubItem]]``                          | `/SubItem </SubItem>`_                      | Link to a sub-item of current item          |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[Home/ItemName]]``                     | `Home/ItemName <Home/ItemName>`_            | Link to a subitem of Home item              |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[/filename.txt]]``                     | `/filename.txt </filename.txt>`_            | Link to a sub-item called Filename.txt      |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[users/JoeDoe]]``                      | `users/JoeDoe <users/JoeDoe>`_              | Link to a user's home item in user namespace|
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[AltItem||class="redirect"]]``         | `AltItem is displayed immediately`          | Type /+modify/<item> in address bar to edit |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+

External Links
--------------

+----------------------------------------------------------------+-----------------------------------------------------------------------+------------------------------------------+
| Markup                                                         | Result                                                                | Comments                                 |
+================================================================+=======================================================================+==========================================+
| ``[[https://moinmo.in/]]``                                     | https://moinmo.in/                                                    | External link                            |
+----------------------------------------------------------------+-----------------------------------------------------------------------+------------------------------------------+
| ``[[https://moinmo.in/|MoinMoin Wiki]]``                       | `MoinMoin Wiki <https://moinmo.in/>`_                                 | Named External link                      |
+----------------------------------------------------------------+-----------------------------------------------------------------------+------------------------------------------+
| ``[[MeatBall:InterWiki]]``                                     | `MeatBall:InterWiki <http://meatballwiki.org/wiki/InterWiki>`_        | Link to an item on an external Wiki      |
+----------------------------------------------------------------+-----------------------------------------------------------------------+------------------------------------------+
| ``[[MeatBall:InterWiki|InterWiki page on MeatBall]]``          | `InterWiki page on MeatBall <http://meatballwiki.org/wiki/InterWiki>`_| Named link to an item on an external Wiki|
+----------------------------------------------------------------+-----------------------------------------------------------------------+------------------------------------------+
| ``[[mailto:user@example.com]]``                                | `mailto:user@example.com <mailto:user@example.com>`_                  | Mailto link                              |
+----------------------------------------------------------------+-----------------------------------------------------------------------+------------------------------------------+


Images and Transclusions
========================

Transclusion syntax is defined as follows: ::

  {{<target>|<optional alternate text>|<optional parameters>}}

  {{bird.jpg|rare yellow bird|class=center}}


- `<target>` is a relative or absolute URL pointing to an image, video, audio, or web page.
- `<optional alternate text>` has several potential uses:

   - Screen readers used by visually impaired users will speak the text.
   - The alternate text may be displayed by the browser if the URL is broken.
   - Search engine crawlers may use the text to index the page or image.
- `optional parameters` may be used to resize or position the target.

   - the browser will automatically resize the image to fit the enclosing container
     by specifying either class=resize or width=100% height=auto
   - Images or other targets can be resized on the client side by specifying
     an option of `width=nn` or `height=nn` where nn is the desired size in pixels.
   - If Pillow is installed on the server, JPEG (or JPG) images can be resized
     on the server by specifying an option of `&w=nn` or `&h=nn` where nn is the
     desired size in pixels.
   - Images embedded within text can be positioned relative to a line of text by
     using `class=bottom`, `class=top` or `class="middle"`.
   - Images displayed as block elements my be floated left or right by using
     `class="left"` or `class=right` respectively, or centered by using `class=center`.

+----------------------------------------------------+---------------------------------------+
| Markup                                             | Comment                               |
+====================================================+=======================================+
| ``text {{example.png}} text``                      | Embed example.png inline              |
+----------------------------------------------------+---------------------------------------+
| ``text {{example.png||class=top height=96}} text`` | Embed example.png inline              |
+----------------------------------------------------+---------------------------------------+
|                                                    |                                       |
| ``{{example.png||class=center}}``                  | example.png as centered image         |
|                                                    |                                       |
+----------------------------------------------------+---------------------------------------+
| ``{{https://static.moinmo.in/logos/moinmoin.png}}``| example.png aligned left, not float   |
+----------------------------------------------------+---------------------------------------+
| ``{{ItemName}}``                                   | Transclude (embed the contents of)    |
|                                                    | ItemName                              |
+----------------------------------------------------+---------------------------------------+
| ``{{/SubItem}}``                                   | Transclude SubItem                    |
+----------------------------------------------------+---------------------------------------+
| ``{{ example.jpg || class=resize }}``              | browser will automatically resize     |
|                                                    | image to fit the enclosing container  |
+----------------------------------------------------+---------------------------------------+
| ``{{ example.jpg || width=20, height=100 }}``      | Resizes example.png by using HTML     |
|                                                    | tag attributes                        |
+----------------------------------------------------+---------------------------------------+
| ``{{ example.jpg || &w=20 }}``                     | Resizes example.png by using server-  |
|                                                    | side compression, requires PIL        |
+----------------------------------------------------+---------------------------------------+
| ``{{ https://moinmo.in/ || width=800 }}``          | Resizes the ``object`` which is       |
|                                                    | embedded using HTML tags. Here markup |
|                                                    | like ``&w=800`` will not work.        |
+----------------------------------------------------+---------------------------------------+

**Extra Info**:

Markup like ``{{ example.jpg || &w=20 }}``, simply adds ``&w`` to the
``src`` URL of the image, the Python Imaging Library (PIL)
understands that it has to compress the image on the server side and
render as shrinked to size ``20``.

For markup like ``{{ example.jpg || width=20, height=100 }}`` we
currently allow only the ``width`` and ``height`` (anything
else is ignored) to be added as attributes in the HTML, however
one can, add anything to the query URL using ``&``, like ``&w``
in the example above.

Most browsers will display a large blank space when a web page using
an https protocol is transcluded into a page using http protocol.
Transcluding a png image using an https protocol into an http protocol
page displays OK in all browsers.


Blockquotes and Indentations
============================

**Markup**: ::

 indented text
  text indented to the 2nd level

**Result**:

 indented text
  text indented to the 2nd level


Lists
=====

.. warning::
 * All Moin Wiki list syntax (including that for unordered lists,
   ordered lists and definition lists) requires a leading space before
   each item in the list.
 * Unfortunately, reStructuredText does not allow leading whitespace
   in code samples, so the example markup here will not work if copied
   verbatim, and requires
   that each line of the list be indented by one space in order to
   be valid Moin Wiki markup.
 * This is also an **reSTTODO**

Unordered Lists
---------------

**Markup**: ::

 * item 1
 * item 2 (preceding white space)
  * item 2.1
   * item 2.1.1
 * item 3
  . item 3.1 (bulletless)
 . item 4 (bulletless)
  * item 4.1
   . item 4.1.1 (bulletless)

**Result**:

 - item 1

 - item 2 (preceding white space)

  - item 2.1

   - item 2.1.1

 - item 3

  - item 3.1 (bulletless)

 - item 4 (bulletless)

  - item 4.1

   - item 4.1.1 (bulletless)

**Note**:
 - Moin markup allows a square, white and a bulletless item for
   unordered lists, these cannot be shown in reST documents.

Ordered Lists
---------------

With Numbers
************

**Markup**: ::

 1. item 1
   1. item 1.1
   1. item 1.2
 1. item 2

**Result**:

 1. item 1

   1. item 1.1

   2. item 1.2

 2. item 2

With Roman Numbers
******************

**Markup**: ::

 I. item 1
   i. item 1.1
   i. item 1.2
 I. item 2

**Result**: ::

 I. item 1

   i. item 1.1

   ii. item 1.2

 II. item 2

With Letters
************

**Markup**: ::

 A. item 1
   a. item 1.1
   a. item 1.2
 A. item 2

**Result**:

 A. item 1

   a. item 1.1

   b. item 1.2

 B. item 2

Specify a Starting Point
************************

When there is a need to start an ordered list at a specific number,
use the format below. This works for ordered lists using letters and
roman numerals.

**Markup**: ::


 1.#11 eleven
 1. twelve
    i.#11 roman numeral xi
 1. thirteen

 A.#11 letter K
 A. letter J


**Result**: ::

 11. eleven
 12. twelve
    xi.roman numeral xi
 13. thirteen

 K. letter K
 J. letter J

Definition Lists
================

**Markup**: ::

 term:: definition
 object::
 :: description 1
 :: description 2

**Result**:

 term
  definition
 object
  | description 1
  | description 2

**Notes**:
 - reStructuredText does not support multiple definitions for a
   single term, so a line break has been forced to illustrate the
   appearance of several definitions.
 - Using the prescribed Moin Wiki markup will, in fact, produce two
   separate definitions in MoinMoin (using separate ``<dd>`` tags).

Horizontal Rules
================

To create a horizontal rule, start a line with 4 or more hyphen (-) characters. Nine (or more) characters creates a line of maximum height.

**Markup**: ::

 Text
 ----
 Text

**Result**:

Text

----

Text

Tables
======

Moin wiki markup supports table headers and footers. To indicate the
first row(s) of a table is a header, insert a line of 3 or more =
characters. To indicate a footer, include a second line of =
characters after the body of the table.

**Markup**: ::

 ||Head A ||Head B ||Head C ||
 =============================
 ||a      ||b      ||c      ||
 ||x      ||y      ||z      ||

**Result**:

====== ====== ======
Head A Head B Head C
====== ====== ======
a      b      c
x      y      z
====== ====== ======

Table Styling
-------------

To add styling to a table, enclose one or more parameters within angle
brackets at the start of any table cell. Options for tables must be
within first cell of first row. Options for rows must be within first
cell of the row. Separate multiple options with a blank character.

================================== ===========================================================
Markup                             Effect
================================== ===========================================================
<tableclass="zebra moin-sortable"> Adds one or more CSS classes to the table
<rowclass="orange">                Adds one or more CSS classes to the row
<class="green">                    Adds one or more CSS classes to the cell
<tablestyle="color: red;">         Add CSS styling to table
<rowstyle="font-size: 140%; ">     Add CSS styling to row
<style="text-align: right;">       Add CSS styling to cell
<bgcolor="#ff0000">                Add CSS background color to cell
<rowbgcolor="#ff0000">             Add CSS background color to row
<tablebgcolor="#ff0000">           Add CSS background color to table
width                              Add CSS width to cell
tablewidth                         Add CSS width to table
id                                 Add HTML ID to cell
rowid                              Add HTML ID to row
tableid                            Add HTML ID to table
rowspan                            Add HTML rowspan attribute to cell
colspan                            Add HTML colspan attribute to cell
caption                            Add HTML caption attribute to table
<80%>                              Set cell width, setting one cell effects entire table column
<(>                                Align cell contents left
<)>                                Align cell contents right
<:>                                Center cell contents
`<|2>`                             Cell spans 2 rows (omit a cell in next row)
<-2>                               Cell spans 2 columns (omit a cell in this row)
<#0000FF>                          Change background color of a table cell
<rowspan="2">                      Same as `<|2>` above
<colspan="2">                      Same as <-2> above
-- no content --                   An empty cell has same effect as <-2> above
`===`                              A line of 3+ "=" separates table header, body and footer
================================== ===========================================================

Table Styling Example
---------------------

**Markup**: ::

 ||Head A||Head B||
 ===
 ||normal text||normal text||
 ||<|2>cell spanning 2 rows||cell in the 2nd column||
 ||cell in the 2nd column of the 2nd row||
 ||<rowstyle="font-weight: bold;" class="monospaced">monospaced text||bold text||

 ||<tableclass="no-borders">A||B||C||
 ||D||E||F||

**Result**:


+----------------------+---------------------------------------+
|Head A                |Head B                                 |
+======================+=======================================+
| normal text          |normal text                            |
+----------------------+---------------------------------------+
| cell spanning 2 rows | cell in the 2nd column                |
|                      +---------------------------------------+
|                      | cell in the 2nd column of the 2nd row |
+----------------------+---------------------------------------+
|``monospaced text``   |**bold text**                          |
+----------------------+---------------------------------------+

| A B C
| D E F

Verbatim Display
----------------

To show plain text preformatted code, just enclose the text in
three or more curly braces.

**Markup**: ::

 {{{
 no indentation example
 }}}

    {{{{
    {{{
    indentation; using 4 curly braces to show example with 3 curly braces
    }}}
    }}}}

**Result**: ::

 no indentation example

    {{{
    indentation; using 4 curly braces to show example with 3 curly braces
    }}}

Parsers
=======

Syntax Highlighting
-------------------

**Markup**: ::

 {{{#!highlight python
 def hello():
    print "Hello World!"
 }}}

**Result**:

.. code-block:: python

    def hello():
        print "Hello, world!"

creole, rst, markdown, docbook, and mediawiki
---------------------------------------------

To add a small section of markup using another parser, follow
the example below replacing "creole" with the target parser
name. The moinwiki parser does not have the facility to place
table headings in the first column, but the creole parser can
be used to create the desired table.

**Markup**: ::

 {{{#!creole
 |=X|1
 |=Y|123
 |=Z|12345
 }}}

**Result**:

======= =======
 X       1
 Y       123
 Z       12345
======= =======

csv
---

The default separator for CSV cells is a semi-colon (;). The
example below specifies a comma (,) is to be used as the separator.

**Markup**: ::

 {{{#!csv ,
 Fruit,Color,Quantity
 apple,red,5
 banana,yellow,23
 grape,purple,126
 }}}

**Result**:

======= ======= =======
 Fruit   Color   Quantity
======= ======= =======
 apple   red     5
 banana  yellow  23
 grape   purple  126
======= ======= =======

wiki
----

The wiki parser is the moinwiki parser. If there is a need to
emphasize a section, pass some predefined classes to the wiki
parser.

**Markup**: ::

 {{{#!wiki solid/orange
 * plain
 * ''italic''
 * '''bold'''
 * '''''bold italic.'''''
 }}}

**Result**:

 - plain
 - ''italic''
 - '''bold'''
 - '''''bold italic.'''''

Admonitions
-----------

Admonitions are used to draw the reader's attention to an important
paragraph. There are nine admonition types: attention, caution,
danger, error, hint, important, note, tip, and warning.


**Markup**: ::

 {{{#!wiki caution
 '''Don't overuse admonitions'''

 Admonitions should be used with care. A page riddled with admonitions
 will look restless and will be harder to follow than a page where
 admonitions are used sparingly.
 }}}

**Result**:

.. caution::
 '''Don't overuse admonitions'''

 Admonitions should be used with care. A page riddled with admonitions
 will look restless and will be harder to follow than a page where
 admonitions are used sparingly.

CSS classes for use with the wiki parser, tables, comments, and links
---------------------------------------------------------------------

 - Background colors: red, green, blue, yellow, or orange
 - Borders: solid, dashed, or dotted
 - Text-alignment: left, center, right, or justify
 - Admonitions: attention, caution, danger, error, hint, important, note, tip, warning
 - Tables: moin-sortable, no-borders
 - Comments: comment
 - Position parsers and tables: float-left, float-right, inline, middle, clear-right, clear-left or clear-both
 - Links with browser redirection: redirect

Variables
=========

Variables within the content of a moin wiki item are transformed
when the item is saved. An exception is if the item has a tag of
'''template''', then no variables are processed. This makes variables
particularly useful within template items. Another frequent use is to
add signatures (@SIG@) to a comment within a discussion item.

Variable expansion is global and happens everywhere within an
item, including code displays, comments, tables, headings, inline
parsers, etc.. Variables within transclusions are not expanded
because they are not part of the including item's content.

**TODO:** Allow wiki admins and users to add custom variables.
There is no difference between system date format and user date
format in Moin 2, fix code or docs.

Predefined Variables
--------------------

+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|Variable   |Description                              |Resulting Markup                           |Example Rendering                                    |
+===========+=========================================+===========================================+=====================================================+
|@PAGE@     |Name of the item (useful for templates)  |HelpOnPageCreation                         |HelpOnPageCreation                                   |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@ITEM@     |Name of the item (useful for templates)  |HelpOnPageCreation                         |HelpOnPageCreation                                   |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@TIMESTAMP@|Raw time stamp                           |2004-08-30T06:38:05Z                       |2004-08-30T06:38:05Z                                 |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@DATE@     |Current date in the system format        |<<Date(2004-08-30T06:38:05Z)>>             |<<Date(2004-08-30T06:38:05Z)>>                       |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@TIME@     |Current date and time in the user format |<<DateTime(2004-08-30T06:38:05Z)>>         |<<DateTime(2004-08-30T06:38:05Z)>>                   |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@ME@       |user's name or "anonymous"               |TheAnarcat                                 |TheAnarcat                                           |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@USERNAME@ |user's name or his domain/IP             | TheAnarcat                                |TheAnarcat                                           |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@USER@     |Signature "-- loginname"                 |-- TheAnarcat                              |-- TheAnarcat                                        |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@SIG@      |Dated Signature "-- login name date time"|-- TheAnarcat <<DateTime(...)>>            |-- TheAnarcat <<DateTime(2004-08-30T06:38:05Z)>>     |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@EMAIL@    |<<MailTo()>> macro, obfuscated email     |<<MailTo(user AT example DOT com)          |user@example.com OR user AT example DOT com          |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+
|@MAILTO@   |<<MailTo()>> macro                       |<<MailTo(testuser@example.com)             |testuser@example.com, no obfuscation                 |
+-----------+-----------------------------------------+-------------------------------------------+-----------------------------------------------------+

**Notes:**

 - @PAGE@ and @ITEM@ results are identical, item being a moin 2
   term and page a moin 1.x term.

 - If an editor is not logged in, then any @EMAIL@ or @MAILTO@
   variables in the content are made harmless by inserting a space
   character. This prevents a subsequent logged in editor from adding
   his email address to the item accidentally.

Macros
======

Macros are extensions to standard markup that allow developers to add
extra features. The following is a table of MoinMoin's macros.

+-------------------------------------------+------------------------------------------------------------+
| Markup                                    | Comment                                                    |
+===========================================+============================================================+
| ``<<Anchor(anchorname)>>``                | Inserts an anchor named "anchorname"                       |
+-------------------------------------------+------------------------------------------------------------+
| ``<<BR>>``                                | Inserts a forced linebreak                                 |
+-------------------------------------------+------------------------------------------------------------+
| ``<<Date()>>``                            | Inserts current date, or unix timestamp or ISO 8601 date   |
+-------------------------------------------+------------------------------------------------------------+
| ``<<DateTime()>>``                        | Inserts current datetime, or unix timestamp or ISO 8601    |
+-------------------------------------------+------------------------------------------------------------+
| ``<<GetText(Settings)>>``                 | Loads I18N texts, Einstellungen if browser is set to German|
+-------------------------------------------+------------------------------------------------------------+
| ``<<GetVal(WikiDict,var1)>>``             | Loads var1 value from metadata of item named WikiDict      |
+-------------------------------------------+------------------------------------------------------------+
| ``<<FootNote(Note here)>>``               | Inserts a footnote saying "Note here"                      |
+-------------------------------------------+------------------------------------------------------------+
| ``<<FontAwesome(name,color,size)>>``      | Displays Font Awsome icon, color and size are optional     |
+-------------------------------------------+------------------------------------------------------------+
| ``<<Icon(my-icon.png)>>``                 | Displays icon from /static/img/icons                       |
+-------------------------------------------+------------------------------------------------------------+
| ``<<Include(ItemOne/SubItem)>>``          | Embeds the contents of ``ItemOne/SubItem`` inline          |
+-------------------------------------------+------------------------------------------------------------+
| ``<<ItemList()>>``                        | Lists subitems of current item, see notes for options      |
+-------------------------------------------+------------------------------------------------------------+
| ``<<MailTo(user AT example DOT org,       | If the user is logged in this macro will display           |
| write me)>>``                             | ``user@example.org``, otherwise it will display the        |
|                                           | obfuscated email address supplied                          |
|                                           | (``user AT example DOT org``)                              |
|                                           | The second parameter containing link text is optional.     |
+-------------------------------------------+------------------------------------------------------------+
| ``<<MonthCalendar()>>``                   | Shows a monthly calendar in a table form,                  |
|                                           | see notes for details                                      |
+-------------------------------------------+------------------------------------------------------------+
| ``<<RandomItem(3)>>``                     | Inserts names of 3 random items                            |
+-------------------------------------------+------------------------------------------------------------+
| ``<<ShowIcons()>>``                       | Displays all icons in /static/img/icons directory          |
+-------------------------------------------+------------------------------------------------------------+
| ``<<ShowSmileys()>>``                     | Displays available smileys and the corresponding markup    |
+-------------------------------------------+------------------------------------------------------------+
| ``<<ShowUserGroup()>>``                   | Displays metadata defined in usergroup attribute           |
+-------------------------------------------+------------------------------------------------------------+
| ``<<ShowWikiDict()>>``                    | Displays metadata defined in wikidict attribute            |
+-------------------------------------------+------------------------------------------------------------+
| ``<<SlideShow()>>``                       | Displays a link to start a slideshow for the current item  |
+-------------------------------------------+------------------------------------------------------------+
| ``<<TableOfContents(2)>>``                | Shows a table of contents up to level 2                    |
+-------------------------------------------+------------------------------------------------------------+
| ``<<TitleIndex()>>``                      | Lists all itemnames for the namespace of the current item, |
|                                           | grouped by initials                                        |
+-------------------------------------------+------------------------------------------------------------+
| ``<<Verbatim(`same` __text__)>>``         | Inserts text as entered, no markup rendering               |
+-------------------------------------------+------------------------------------------------------------+

Notes
-----

**Date** and **DateTime** macros accept integer timestamps and ISO 8601 formatted date-times:

    - <<Date(1434563755)>>
    - <<Date(2002-01-23T12:34:56)>>

**Footnotes** are created by placing the macro within text. By default footnotes are placed at the bottom
of the page. Explicit placement of footnotes is accomplished by calling the macro without a parameter.

    - text<<FootNote(A macro is enclosed in double angle brackets, and'''may''' have markup.)>> more text
    - <<FootNote()>>

The **FontAwesome** macro displays FontAwesome fonts.  See https://fontawesome.com/search?o=r&m=free
for the list of fonts available with FontAwesome version 6.

The **FontAwesome** "name" parameter may include multiple space-separated names.
The free fonts are divided into 3 groups: solid, regular (outline), and brands. If the name field consists of
a single font name, then the font from the solid group is displayed. To display a font from the regular group,
add "regular" to the name field. To display a font from the brands group, add "brands".

The **FontAwesome** color field may be an HTML color name or a hex digit color code with a leading #:
#f00 or #F80000.
The size field must be an unsigned decimal integer or float that will adjust the size of the character
relative to the current font size: 2 or 2.0 will create double the character size, .5 will create a character
half the current size.

    - <<FontAwesome(thumbs-up,#f00,2)>> is similar to
    - <<FontAwesome(regular thumbs-up,red,2)>> but different from these spinners
    - <<FontAwesome(spin spinner,plum,2.5)>> <<FontAwesome(fan spin-reverse,orange,2.5)>>

The **Include** macro <<Include(my.png)>> produces results identical to the transclusion {{my.png}}.
It is more flexible than a transclusion because it supports multiple parameters and the first parameter may
be any regrex starting with a `^`. The include macro accepts 3 parameters where the second parameter is a
heading and the third parameter a heading level between 1 and 6:

    - <<Include(^zi)>> embeds all wiki items starting with `zi`.
    - <<Include(moin.png,My Favorite icon, 6)>>

The **ItemList** macro accepts multiple named parameters: item, startswith, regex, ordered and display.

    - <<ItemList(item="Foo")>> lists subitems of Foo item
    - <<ItemList(ordered='True')>> displays ordered list of subitems, default is unordered
    - <<ItemList(startswith="Foo")>> lists subitems starting with Foo
    - <<ItemList(regex="Foo$")>> lists subitems ending with Foo
    - <<ItemList(skiptag="template")>> ignore items with this tag
    - <<ItemList(display="FullPath")>> default, displays full path to subitems
    - <<ItemList(display="ChildPath")>> displays last component of the FullPath, including the '/'
    - <<ItemList(display="ChildName")>> displays subitem name
    - <<ItemList(display="UnCameled")>> displays "fooBar" as "foo Bar"

The **MonthCalendar** macro accepts multiple named parameters: item, year, month, month_offset,
fixed_height and anniversary.

    - <<MonthCalendar>>  Calendar of current month for current page
    - <<MonthCalendar(month_offset=-1)>>  Calendar of last month
    - <<MonthCalendar(month_offset=+1)>>  Calendar of next month
    - <<MonthCalendar(item="SampleUser",month=12)>>  Calendar of Page SampleUser, this year's december
    - <<MonthCalendar(month=12)>>  Calendar of current Page, this year's december
    - <<MonthCalendar(year=2022,month=12)>>  Calendar of December, 2022

The **SlideShow** macro creates a link to start a presentation for the current item. The slides
are separated by level 1 and 2 headings. The text before the first heading is ignored. Navigation
within the slideshow can be controlled via corresponding buttons at the edge or bottom of the
browser screen or using the left and right arrow keys.


Smileys and Icons
=================

This table shows moin smiley markup, the rendering of smiley icons cannot be shown in Rest markup.

+---------+---------+---------+---------+
| ``X-(`` | ``:D``  | ``<:(`` | ``:o``  |
+---------+---------+---------+---------+
| ``:(``  | ``:)``  | ``B)``  | ``:))`` |
+---------+---------+---------+---------+
| ``;)``  | ``/!\`` | ``<!>`` | ``(!)`` |
+---------+---------+---------+---------+
| ``:-?`` | ``:\``  | ``>:>`` | ``|)``  |
+---------+---------+---------+---------+
| ``:-(`` | ``:-)`` | ``B-)`` | ``:-))``|
+---------+---------+---------+---------+
| ``;-)`` | ``|-)`` | ``(./)``| ``{OK}``|
+---------+---------+---------+---------+
| ``{X}`` | ``{i}`` | ``{1}`` | ``{2}`` |
+---------+---------+---------+---------+
| ``{3}`` | ``{*}`` | ``{o}`` |         |
+---------+---------+---------+---------+

Comments
--------

There are three ways to add comments to a page. Lines starting with ##
can be seen only by page editors. Phrases enclosed in `/*` and `*/`
and wiki parser section blocks of text with a class of "comment" may
be hidden or visible depending upon user settings or actions.

**Markup**: ::

 ## Lines starting with "##" may be used to give instructions
 ## to future page editors.

 Click on the "Comments" button within Item Views to toggle the /* comments */ visibility.

 {{{#!wiki comment/dashed
 This is a wiki parser section with class "comment dashed".

 Its visibility gets toggled by clicking on the comments button.
 }}}



**Result**:

Click on the "Comments" button within Item Views to toggle the visibility.

**Notes**:
 - The toggle display feature does not work on reST documents, so there is
   no way to see the hidden comments.
