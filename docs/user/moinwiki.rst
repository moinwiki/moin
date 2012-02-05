.. role:: underline
.. role:: strikethrough
.. role:: sup
.. role:: sub


==========================
Moin Wiki markup overview
==========================

The report follows the moin 1.9 help page and reports syntaxes that do not match 1.9 help syntax documentation.
The structure and order has been matched with other markup rst files namely creoleWiki.rst and mediaWiki.rst at http://hg.moinmo.in/moin/2.0-dev/file/42d8cde592fb/docs/user

Features currently not working with moin's Wiki parser are marked with **MOINTODO**.

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
 - Also, whitespace between the first word of the heading and the opening equals sign will not be shown in the output (ie. leading whitespace is stripped).

Text formatting
===============

The following is a table of inline markup that can be used to control text formatting in Moin.

+-------------------------------------+---------------------------------------+
| Markup                              | Result                                |
+=====================================+=======================================+
| ``'''Bold Text'''``                 | **Bold text**                         |
+-------------------------------------+---------------------------------------+
| ``''Italic''``                      | *Italic*                              |
+-------------------------------------+---------------------------------------+
| ```Monospace```                     | ``Monospace``                         |
+-------------------------------------+---------------------------------------+
| ``{{{Code}}}``                      | ``Code``                              |
+-------------------------------------+---------------------------------------+
| ``__Underline__``                   | :underline:`Underline`                |
+-------------------------------------+---------------------------------------+
| ``^Super^Script``                   | SuperScript                           |
+-------------------------------------+---------------------------------------+
| ``,,Sub,,Script``                   | SubScript                             |
+-------------------------------------+---------------------------------------+
| ``~-Smaller-~``                     |	Smaller                               |
+-------------------------------------+---------------------------------------+
| ``~+Larger+~``                      | Larger                                |
+-------------------------------------+---------------------------------------+
| ``--(Stroke)--``                    | :strikethrough:`Stroke`               |
+-------------------------------------+---------------------------------------+

Hyperlinks
==========

Internal Links
--------------

+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| Markup                                    | Result                                      | Comments                                    |
+===========================================+=============================================+=============================================+
| ``ItemName``                              | `ItemName <ItemName>`_                      | Link to an item                             |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
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
| ``../SiblingItem``                        | `../SiblingItem <../SiblingItem>`_          | Link to a sibling of the current item       |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[../SiblingItem]]``                    | `../SiblingItem <../SiblingItem>`_          | Link to a sibling of the current item       |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``/SubItem``                              | `/SubItem </SubItem>`_                      | Link to a sub-item                          |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[/SubItem]]``                          | `/SubItem </SubItem>`_                      | Link to a sub-item                          |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``Home/ItemName``                         | `Home/ItemName <Home/ItemName>`_            | Link to an item                             |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+
| ``[[/filename.txt]]``                     | `/filename.txt </filename.txt>`_            | Link to a sub-item called Filename.txt      |
+-------------------------------------------+---------------------------------------------+---------------------------------------------+

External Links
--------------

+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+
| Markup                                                         | Result                                                                       | Comments                                 |
+================================================================+==============================================================================+==========================================+
| ``http://moinmo.in/``                                          | http://moinmo.in/                                                            | External link                            |
+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+
| ``[[http://moinmo.in/]]``                                      | http://moinmo.in/                                                            | External link                            |
+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+
| ``[[http://moinmo.in/|MoinMoin Wiki]]``                        | `MoinMoin Wiki <http://moinmo.in/>`_                                         | Named External link                      |
+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+
| ``MeatBall:InterWiki``                                         | `MeatBall:InterWiki <http://www.usemod.com/cgi-bin/mb.pl?InterWiki>`_        | Link to an item on an external Wiki      |
+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+
| ``[[MeatBall:InterWiki|InterWiki page on MeatBall]]``          | `InterWiki page on MeatBall <http://www.usemod.com/cgi-bin/mb.pl?InterWiki>`_| Named link to an item on an external Wiki|
+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+
| ``user@example.com``                                           | `user@example.com <mailto:user@example.com>`_                                | Mailto link                              |
+----------------------------------------------------------------+------------------------------------------------------------------------------+------------------------------------------+

**MOINTODO**: every syntax above that is not in a double square bracets ( [[]] ) does not work on moin2, it is also not listed to be a valid syntax on the moin2 syntax help page.

Images and Transclusions
========================

+---------------------------------------------------+---------------------------------------+
| Markup                                            | Comment                               |
+===================================================+=======================================+
| ``{{example.png}}``                               | Embed example.png inline              |
+---------------------------------------------------+---------------------------------------+
| ``{{http://static.moinmo.in/logos/moinmoin.png}}``| Embed example.png inline              |
+---------------------------------------------------+---------------------------------------+
| ``{{ItemName}}``                                  | Transclude (embed the contents of)    |
|                                                   | ItemName inline.                      |
+---------------------------------------------------+---------------------------------------+
| ``{{/SubItem}}``                                  | Transclude SubItem inline.            |
+---------------------------------------------------+---------------------------------------+

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
   All Moin Wiki list syntax (including that for unordered lists, ordered lists and definition lists) requires a leading space before each item in the list.
   Unfortunately, reStructuredText does not allow leading whitespace in code samples, so the example markup here will not work if copied verbatim, and requires
   that each line of the list be indented by one space in order to be valid Moin Wiki markup.
   This is also an **RSTTODO**

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
 - moin markup allows a square, white and a bulletless item for unordered lists, these cannot be chosen in rst

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

**Result**:

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
 - reStructuredText does not support multiple definitions for a single term, so a line break has been forced to illustrate the appearance of several definitions.
   Using the prescribed Moin Wiki markup will, in fact, produce two separate definitions in MoinMoin (using separate ``<dd>`` tags).
  
Tables
======

Tables
------

**Markup**: ::

 ||'''A'''||'''B'''||'''C'''||
 ||1      ||2      ||3      ||
 
**Result**:

======= ======= =======
 A       B       C     
======= ======= =======
 1       2       3     
======= ======= =======

Cell Width
----------

**Markup**: ::

 ||minimal width ||<99%>maximal width ||
 
**Result**:

+---------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------+
| minimal width | maximal width (will take the maximum screen space)                                                                                                           |
+---------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Notes**:
 - **MOINTODO:** the cell width does not work in moin 2.
 - reStructuredText does not support percentage cell width so cell has been made long manually. In MoinMoin the second cell will take up the maximum amount of horizontal space.

Spanning Rows and Columns
-------------------------

**Markup**: ::
 
 ||<|2> cell spanning 2 rows ||cell in the 2nd column ||
 ||cell in the 2nd column of the 2nd row ||
 ||<-2> cell spanning 2 columns ||
 ||||use empty cells as a shorthand ||
 
**Result**:

+----------------------+---------------------------------------+
| cell spanning 2 rows | cell in the 2nd column                |
|                      +---------------------------------------+
|                      | cell in the 2nd column of the 2nd row |
+----------------------+---------------------------------------+
| cell spanning 2 columns                                      |
+-------------+------------------------------------------------+
|             | use empty cells as a shorthand                 |
+-------------+------------------------------------------------+

**Notes**:
 - **MOINTODO:** use empty cells as a shorthand does not work in moin 2.

Alignment of Cell Contents
--------------------------

**Markup**: ::
 
 ||<^|3> Top (Combined) ||<:> Center (Combined) ||<v|3> Bottom (Combined) ||
 ||<)> Right ||
 ||<(> Left ||
 
**Result**:

+----------------+---------------------------------------+-------------------+
| Top (Combined) |           center (combined)           |                   |
|                +---------------------------------------+                   |
|                |                                 Right |                   |
|                +---------------------------------------+                   |
|                | Left                                  | Bottom (Combined) |
+----------------+---------------------------------------+-------------------+

**Notes**:
 - Text cannot be aligned in reStructuredText, but the text will appear as is described when used in MoinMoin.

HTML-like Options for Tables
----------------------------

**Markup**: ::
 
 ||A ||<rowspan="2"> like <|2> ||
 ||B ||
 ||<colspan="2"> like <-2>||
 
**Result**:

+----------------+---------------+
| A              |               |
+----------------+ like ``<|2>`` |
| B              |               |
+----------------+---------------+
| like <-2>                      |
+--------------------------------+
  
Macros
------

 - ``<<Anchor(anchorname)>>`` inserts a link anchor anchorname
 - ``<<BR>>`` inserts a hard line break
 - ``<<FootNote(Note)>>`` inserts a footnote saying Note
 - ``<<Include(HelpOnMacros/Include)>>`` inserts the contents of the page HelpOnMacros/Include inline
 - ``<<MailTo(user AT example DOT com)>>`` obfuscates the email address user@example.com to users not logged in
 
**Notes**:
 - **MOINTODO:** ``<<Anchor(anchorname)>>`` throws an error ``<<Anchor: execution failed [__init__() takes exactly 2 arguments (1 given)] (see also the log)>>`` in moin 2.
 - **MOINTODO:** ``<<Include(HelpOnMacros/Include)>>`` does not work in moin 2.
 - **MOINTODO:** ``<<MailTo(user AT example DOT com)>>`` throws an error ``<<MailTo: execution failed [__init__() takes exactly 2 arguments (1 given)] (see also the log)>>`` in moin 2.  
 
Smileys and Icons
=================

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
 
Parsers
=======

Verbatim Display
----------------

**Markup**: ::
 
 {{{
 def hello():
  print "Hello World!"
 }}}
 
**Result**: ::

 def hello():
  print "Hello World!"

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

**Notes**:
 - The syntax crashes moin2.

Using the wiki parser with css classes
--------------------------------------

CSS classes for use with wiki parsers include:
 - Background colors: red, green, blue, yellow, or orange
 - Borders: solid, dashed, or dotted
 - Text-alignment: left, center, right, or justify
 - Admonitions: caution, important, note, tip, warning
 - Comments: comment

**Markup**: ::
 
 {{{#!wiki red/solid
 This is wiki markup in a '''div''' with css `class="red solid"`.
 }}}
 
**Result**:

+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| This is wiki markup in a **div** with css `class="red solid"`.                                                                                                       |
+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Notes**:
 - The div cannot be shown in reStructuredText, so a table cell has been made to demonstrate the border produced. In MoinMoin, this border will appear red.

Admonitions
-----------

**Markup**: ::
 
 {{{#!wiki caution
 '''Don't overuse admonitions'''
 
 Admonitions should be used with care. A page riddled with admonitions will look restless and will be harder to follow than a page where admonitions are used sparingly.
 }}}
 
**Result**:

.. warning::
    **Don't overuse admonitions**

    Admonitions should be used with care. A page riddled with admonitions will look restless and will be harder to follow than a page where admonitions are used sparingly.

Comments
--------

**Markup**: ::
 
 {{{#!wiki comment/dotted
 This is a wiki parser section with class "comment dotted" (see HelpOnParsers).

 Its visibility gets toggled the same way.
 }}}
 
**Result**:

+--------------------------------------------------------------------------------+
| This is a wiki parser section with class "comment dotted" (see HelpOnParsers). |
|                                                                                |
| Its visibility gets toggled the same way.                                      |
+--------------------------------------------------------------------------------+

**Notes**:
 - reStructuredText has no support for dotted borders, so a table cell is used to illustrate the border which will be produced. This markup will actually produce a dotted border in MoinMoin.
 - The toggle display feature does not work yet
