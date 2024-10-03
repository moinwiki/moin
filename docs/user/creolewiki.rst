.. role:: bolditalic
.. role:: underline

==========================
WikiCreole markup overview
==========================

Features currently not working with moin's WikiCreole parser are marked with **CREOLETODO**.

Features currently not working with moin's rst parser are marked with **reSTTODO**.

Headings
========

**Markup**: ::

    = Level 1
    == Level 2
    === Level 3
    ==== Level 4
    ===== Level 5
    ====== Level 6

**Result**:

Level 1
=======

**Intentionally not rendered as level 1 so it does not interfere with Sphinx's indexing**

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

Closing equals signs are optional and do not affect the output.
Also, whitespace between the first word of the heading and the opening equals sign will not be shown in the output (ie. leading whitespace is stripped).

Text formatting
===============

The following is a table of inline markup that can be used to format text in Creole.

+-------------------------------------+---------------------------------------+
| Markup                              | Result                                |
+=====================================+=======================================+
| ``**Bold Text**``                   | **Bold text**                         |
+-------------------------------------+---------------------------------------+
| ``//Italic Text//``                 | *Italic Text*                         |
+-------------------------------------+---------------------------------------+
| ``//**Bold and Italic**//``         | :bolditalic:`Bold and Italic`         |
+-------------------------------------+---------------------------------------+
| ``__Underline__``                   | :underline:`Underline`                |
+-------------------------------------+---------------------------------------+
| ``{{{Monospace}}}``                 | ``Monospace``                         |
+-------------------------------------+---------------------------------------+
| ``First line\\Second line``         | | First line                          |
|                                     | | Second line                         |
+-------------------------------------+---------------------------------------+

**reSTTODO**: Restructured Text line blocks are not working in Moin2

Hyperlinks
==========

Internal links
--------------

.. _Item name:
.. _ItemName/Subitem:
.. _/SubItem:
.. _../SiblingItem:
.. _Named Item:
.. _#AnchorName:
.. _Named anchor:
.. _ItemName#AnchorName:
.. _Filename.txt: #

+---------------------------------------+-----------------------------------+-------------------------------------------+
| Markup                                | Result                            | Comment                                   |
+=======================================+===================================+===========================================+
| ``[[ItemName]]``                      | `Item name`_                      | Link to an item                           |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[ItemName|Named Item]]``           | `Named Item`_                     | Named link to an internal item            |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[#AnchorName]]``                   | `#AnchorName`_                    | Link to an anchor in the current item     |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[#AnchorName|Named anchor]]``      | `Named anchor`_                   | Link to a named anchor.                   |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[ItemName#AnchorName]]``           | `ItemName#AnchorName`_            | Link to an anchor in an internal item     |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[ItemName/SubItem]]``              | `ItemName/Subitem`_               | Link to a sub-item of an internal item    |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[../SiblingItem]]``                | `../SiblingItem`_                 | Link to a sibling of the current item     |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[/SubItem]]``                      | `/SubItem`_                       | Link to a sub-item                        |
+---------------------------------------+-----------------------------------+-------------------------------------------+
| ``[[attachment:Filename.txt]]``       | `Filename.txt`_                   | Link to a sub-item called Filename.txt.   |
|                                       |                                   | Note that this is for MoinMoin 1.x        |
|                                       |                                   | compatability and is deprecated in favour |
|                                       |                                   | of the more convenient ``[[/SubItem]]``   |
|                                       |                                   | syntax                                    |
+---------------------------------------+-----------------------------------+-------------------------------------------+

External links
--------------

.. _http\://www.example.com: http://www.example.com
.. _http\://www.example.com: http://www.example.com
.. _InterWiki item on MeatBall: http://meatballwiki.org/wiki/InterWiki
.. _mailto\:user@example.org: user@example.org

+-------------------------------------------------------+-------------------------------+-------------------------------------+
| Markup                                                | Result                        | Comment                             |
+=======================================================+===============================+=====================================+
| ``http://www.example.com``                            | `http://www.example.com`_     | External link                       |
+-------------------------------------------------------+-------------------------------+-------------------------------------+
| ``[[http://www.example.com]]``                        | `http://www.example.com`_     | External link                       |
+-------------------------------------------------------+-------------------------------+-------------------------------------+
| ``[[MeatBall:InterWiki|InterWiki item on MeatBall]]`` | `InterWiki item on MeatBall`_ | Link to an item on an external Wiki |
+-------------------------------------------------------+-------------------------------+-------------------------------------+
| ``[[mailto:user@example.org]]``                       | `mailto:user@example.org`_    | Mailto link                         |
+-------------------------------------------------------+-------------------------------+-------------------------------------+

Images and Transclusions
========================

+------------------------------------+---------------------------------------+
| Markup                             | Comment                               |
+====================================+=======================================+
| ``{{example.png}}``                | Embed example.png inline              |
+------------------------------------+---------------------------------------+
| ``{{example.png|Alt text}}``       | Embed example.png inline or display   |
|                                    | "Alt text" if not available           |
+------------------------------------+---------------------------------------+
| ``{{ItemName}}``                   | Transclude (embed the contents of)    |
|                                    | ItemName inline.                      |
+------------------------------------+---------------------------------------+
| ``{{/SubItem}}``                   | Transclude SubItem inline.            |
+------------------------------------+---------------------------------------+

Paragraphs
==========

**Markup**: ::

 You can leave an empty line to start a new paragraph.

 Single breaks are ignored.
 To force a line break, use <<BR>> or \\.

**Result**:

You can leave an empty line to start a new paragraph.

| Single breaks are ignored. To force a line break, use
| or
| .

**reSTTODO**: reStructuredText line blocks are not working in Moin2

Horizontal rules
================

**Markup**: ::

    A horizontal rule can be added by typing four dashes.

    ----

    This text will be displayed below the rule.

**Result**:

A horizontal rule can be added by typing four dashes.

----

This text will be displayed below the rule.

Preformatted text
=================

**Markup**:  ::

    {{{
    This text will [[escape]] **special** WikiCreole //markup//
        It will also preserve indents

    And whitespace.
    }}}
    ~[[This text will not be a link, because it uses the tilde (~) escape character]]

**Result**: ::

    This text will [[escape]] **special** WikiCreole //markup//
        It will also preserve indents

    And whitespace.

[[This text will not be a link, because it uses the tilde (~) escape character]]

**Notes**:

This tilde character (``~``) makes the parser ignore the character following it, which can be used to prevent links from appearing as links or prevent bold text from appearing as bold. For example "``~**Not bold~**``" would output "\**Not bold**").

Syntax Highlighting
-------------------

**Markup**: ::

    {{{
    #!python
    #Python syntax highlighting
    import this

    def spam():
        print('Spam, glorious spam!')

    spam()
    }}}

**Result**: ::

    #Python syntax highlighting
    import this

    def spam():
        print('Spam, glorious spam!')

    spam()

**CREOLETODO**:The use of syntax highlighting currently crashes moin.

Lists
=====

Ordered lists
-------------

Ordered lists are formed of lines that start with number signs (``#``).
The number of '#' signs at the beginning of a line determines the current level.

**Markup**: ::

 # First item
 # Second item
 ## First item (second level)
 ## Second item (second level)
 ### First item (third level)
 # Third item

**Result**:

1. First item
2. Second item

 #. First item (second level)
 #. Second item (second level)

  #. First item (third level)

3. Third item

Unordered lists
---------------

**Markup**: ::

 * List item
 * List item
 ** List item (second level)
 *** List item (third level)
 * List item

**Result**:

- List item
- List item

 - List item (second level)

  - List item (third level)

- List item

Mixed lists
-----------

**Markup**: ::

  # First item
  # Second item
  ** Bullet point one
  ** Bullet point two
  # Third item
  # Fourth item

**Result**:

1. First item
2. Second item

  - Bullet point one
  - Bullet point two

3. Third item
4. Fourth item

Tables
======

**Markup**: ::

|= Header one |= Header two |
| Cell one    | Cell two
| Cell three  | Cell four   |

**Result**:

+------------+------------+
| Header one | Header two |
+============+============+
| Cell one   | Cell two   |
+------------+------------+
| Cell three | Cell four  |
+------------+------------+

**Notes**:

Table cells start with a pipe symbol (``|``), and header cells start with a pipe symbol and equals sign (``|=``).
The closing pipe symbol at the end of a row is optional.

Macros
======

Macros are extensions to standard Creole markup that allow developers to add
extra features. The following is a table of MoinMoin's Creole macros.

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
| ``<<FontAwesome(name,color,size)>>``      | displays Font Awsome icon, color and size are optional     |
+-------------------------------------------+------------------------------------------------------------+
| ``<<Icon(my-icon.png)>>``                 | displays icon from /static/img/icons                       |
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
| ``<<ShowIcons()>>``                       | displays all icons in /static/img/icons directory          |
+-------------------------------------------+------------------------------------------------------------+
| ``<<TableOfContents(2)>>``                | Shows a table of contents up to level 2                    |
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

**FontAwesome** color must be a hex digit color code of either 3 or 6 digits with a leading #: #f00 or #F80000.
FontAwesome size must be an unsigned decimal integer or float that will adjust the size of the character
relative to the current font size: 2 or 2.0 will create double the character size, .5 will create a character
half the current size. Font awesome experts will know about the special "fa" class and the "fa-" name prefixes.
It is acceptable, but not necessary to provide these. See https://fontawesome.com/v4/cheatsheet/

    - <<FontAwesome(thumbs-up,#f00,2)>> is identical to
    - <<FontAwesome(fa fa-thumbs-up fa-2x,#FF0000)>>

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
    - <<ItemList(tag="template")>> only include items with this tag 
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
