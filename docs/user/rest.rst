===============================
ReST (ReStructured Text) Markup
===============================

Features currently not working with moin's ReST parser are marked with **RSTTODO**.

Headings
========

Rather than imposing a fixed number and order of section title adornment styles,
the order enforced will be the order as encountered.
The first style encountered will be an outermost title (like HTML H1), the second style will be a subtitle,
the third will be a subsubtitle, and so on.

The underline below the title must at least be equal to the length of the title itself.  Failure to comply results in messages on the server log. Skipping a heading (e.g. putting an H5 heading directly under an H3) results in a rendering error and an error message will be displayed instead of the expected page.

If any markup appears before the first heading on a page, then the first heading will be an H2 and all subsequent headings will be demoted by 1 level.

**Markup**: ::

 =======
 Level 1
 =======

 Level 2
 =======

 # levels 1 and 2 are not shown below, see top of page and this section heading.

 Level 3
 -------

 Level 4
 *******

 Level 5
 :::::::

 Level 6
 +++++++


**Result**:


Level 3
-------

Level 4
*******

Level 5
:::::::

Level 6
+++++++


Table of Contents
=================

**Markup**: ::

    .. contents::

**Result**:

.. contents::

The table of contents may appear above or floated to the right side due to CSS styling.


Text formatting
===============

The following is a table of inline markup that can be used to format text in Moin.

+----------------------------------------------+---------------------------------------+
| Markup                                       | Result                                |
+==============================================+=======================================+
| ``**Bold Text**``                            | **Bold text**                         |
+----------------------------------------------+---------------------------------------+
| ``*Italic*``                                 | *Italic*                              |
+----------------------------------------------+---------------------------------------+
| ````Inline Literals````                      | ``Inline Literals``                   |
+----------------------------------------------+---------------------------------------+
| ````***nested markup is not supported***```` | ***nested markup is not supported***  |
+----------------------------------------------+---------------------------------------+

Hyperlinks
==========

External Links
--------------

+-----------------------------------------------------------------+--------------------------------------------------------------+
| Markup                                                          | Result                                                       |
+=================================================================+==============================================================+
| ``http://www.python.org/``                                      | http://www.python.org/                                       |
+-----------------------------------------------------------------+--------------------------------------------------------------+
| ``External hyperlinks, like `Python <http://www.python.org/>`_``| External hyperlinks, like `Python <http://www.python.org/>`_ |
+-----------------------------------------------------------------+--------------------------------------------------------------+
| ``External hyperlinks, like Python_.``                          | External hyperlinks, like Python_.                           |
|                                                                 |                                                              |
| ``.. _Python: http://www.python.org/``                          | .. _Python: http://www.python.org/                           |
+-----------------------------------------------------------------+--------------------------------------------------------------+

**Note** A blank is required before the link definition to make the last syntax work correctly.

Internal Links
--------------

**Markup**: ::

 Internal crossreferences, like example_.

 .. _example:

 This is an example crossreference target.

**Result**:

 Internal crossreferences, like example_.

 .. _example:

 This is an example crossreference target.

**Notes**
 - Section titles automatically generate hyperlink targets (the title text is used as the hyperlink name).
 - **RSTTODO** The above syntax does not work in moin right now.

Images
======

**Markup**: ::

 .. image:: png
   :height: 100
   :width: 200
   :scale: 50%
   :alt: text
   :align: right

**Result**:

 .. image:: png

Blockquotes and Indentations
============================

Every additional space before the first word in a line will add an indent before the line.

**Markup**: ::

 indented text
  text indented for the 2nd level

**Result**:

 indented text
  text indented for the 2nd level

**Markup**: ::

  This is an ordinary paragraph, introducing a block quote.

    "It is my business to know things.  That is my trade."

    -- Sherlock Holmes

**Result**:

  This is an ordinary paragraph, introducing a block quote.

    "It is my business to know things.  That is my trade."

    -- Sherlock Holmes

**Notes**
 - A block quote may end with an attribution: a text block beginning with "--", "---",
   or a true em-dash, flush left within the block quote.
 - **RSTTODO** the attribution does not work in moin2.
 - **RSTTODO** indented text should not be displayed the same as term-definition, needs CSS fix

   - term-definition: <dl><dt>term 1</dt><dd><p>Definition 1.</p>
   - indented text: <dl><dd><dl><dt>indented text</dt><dd><p>text indented for the 2nd level</p>

Lists
=====

Unordered Lists
---------------

**Markup**: ::

 - item 1

 - item 2

  - item 2.1

   - item 2.1.1

 - item 3

**Result**:

 - item 1

 - item 2

  - item 2.1

   - item 2.1.1

 - item 3

Ordered Lists
---------------

**Markup**: ::

 1. item 1

    (A) item 1.1
    (#) item 1.2

        i) item 1.2.1
        #) item 1.2.2

 #. item 2

**Result**:

 1. item 1

    (A) item 1.1
    (#) item 1.2

        i) item 1.2.1
        #) item 1.2.2

 #. item 2

**Notes**:
 - Ordered lists can be automatically enumerated using the ``#`` character as demonstrated above. Note that the first item of an ordered list
   auto-enumerated in this fashion must use explicit numbering notation (e.g. ``1.``) in order to select the enumeration sequence type
   (e.g. Roman numerals, Arabic numerals, etc.), initial number (for lists which do not start at "1") and formatting type (e.g. ``1.`` or ``(1)`` or ``1)``). More information on
   enumerated lists can be found in the `reStructuredText documentation <http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#enumerated-lists>`_.
 - One or more blank lines are required before and after reStructuredText lists.
 - **RSTTODO**: Formatting types (1) and 1) do not render correctly in moin2.

Definition Lists
================

Definition lists are formed by an unindented one line term followed by an indented definition.

**Markup**: ::

 term 1
  Definition 1.

 term 2 : classifier
  Definition 2.

 term 3 : classifier one : classifier two
  Definition 3.

**Result**:

term 1
 Definition 1.

term 2 : classifier
 Definition 2.

term 3 : classifier one : classifier two
 Definition 3.

Field Lists
===========

Field lists are part of an extension syntax for directives usually intended for further processing.

**Markup**: ::

    :Date: 2001-08-16
    :Version: 1
    :Authors: Joe Doe

**Result**:

:Date: 2001-08-16
:Version: 1
:Authors: Joe Doe

**Notes**:
 - **RSTTODO**: This could use some CSS changes to enhance the format.

Option lists
============

Option lists are intended to document Unix or DOS command line options.

**Markup**: ::

    -a      command definition
    --a     another command definition
    /S      dos command definition

**Result**:

-a      command definition
--a     another command definition
/S      dos command definition

**Notes**:
 - **RSTTODO**: The above is rendered in a <dl><dd><p> sequence, but there is a lack of CSS to format it.


Backslash Escapes
=================

Sometimes there is a need to use special characters as literal characters, but ReST's syntax gets in the way. Use the backslash character as an escape.

**Markup**: ::

    *hot*

    333. is a float, 333 is an integer.

    \*hot\*

    333\. is a float, 333 is an integer.

**Result**:

*hot*

333. is a float, 333 is an integer.

\*hot\*

333\. is a float, 333 is an integer.


Tables
======

Simple Tables
-------------

Easy markup for tables consisting of two rows. This syntax can have no more than two rows.

**Markup**: ::

 ======= ======= =======
  A       B       C
 ======= ======= =======
  1       2       3
 ======= ======= =======

**Result**:

 ======= ======= =======
  A       B       C
 ======= ======= =======
  1       2       3
 ======= ======= =======


**Markup**: ::

 ======= ======= =======
       foo         Bar
 --------------- -------
  A       B       C
 ======= ======= =======
  1       2       3
 ======= ======= =======

**Result**:

 ======= ======= =======
       foo         Bar
 --------------- -------
  A       B       C
 ======= ======= =======
  1       2       3
 ======= ======= =======

**Note** **RSTTODO** the foo-bar syntax to group header does not work.

Grid Tables
-----------

Complex tables can have any number of rows or columns. They are made by ``|``, ``+``, ``-`` and ``=``.

**Markup**: ::

 +----------------+---------------+
 | A              |               |
 +----------------+ D             |
 | B              |               |
 +----------------+---------------+
 | C                              |
 +--------------------------------+

**Result**:

 +----------------+---------------+
 | A              |               |
 +----------------+ D             |
 | B              |               |
 +----------------+---------------+
 | C                              |
 +--------------------------------+

**Note** **RSTTODO** C does not extend fully up to the end of D.

Grid table column widths can be expanded by adding spaces.

**Markup**: ::

 +---------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------+
 | minimal width | maximal width (will take the maximum screen space)                                                                                                           |
 +---------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Result**:

 +---------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------+
 | minimal width | maximal width (will take the maximum screen space)                                                                                                           |
 +---------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Note** **RSTTODO** The moin2 ReST parser does not add the <colgroup><col width="9%"><col width="91%"> HTML markup. Tables will always be of minimal width (unless there is CSS styling to set tables larger).

Admonitions
===========

Admonitions are used as a caution/notification block.

**Markup**: ::

 .. caution:: Caution!
 .. danger:: Danger!
 .. error:: Error!

 .. note:: This is a paragraph
 .. admonition:: By the way

**Result**:

 .. caution:: Caution!
 .. danger:: Danger!
 .. error:: Error!

 .. note:: This is a paragraph
 .. admonition:: By the way

**Notes**:
 - **RSTTODO**: Admonitions are not working. Generates: <div class="None"> and <p style="">

Comments
========

Comments are not shown on the page but depending on the output formatter they might be included as HTML comments (``<!-- -->``).

**Markup**: ::

 .. This is a comment
 ..
  _so: is this!
 ..
  [and] this!
 ..
  this:: too!
 ..
  |even| this:: !

**Result**:

 .. This is a comment
 ..
  _so: is this!
 ..
  [and] this!
 ..
  this:: too!
 ..
  |even| this:: !

**Note** **RSTTODO** comment markup does not work in moin2.

Literals Blocks
===============

Literal blocks are used to show text as-it-is. i.e no markup processing is done within a literal block.
A minimum (1) indentation is required for the text block to be recognized as a literal block.

**Markup**: ::

 Paragraph with a space between preceding two colons ::

  Literal block

**Result**:

 Paragraph with a space between preceding two colons ::

  Literal block

**Markup**: ::

 Paragraph with no space between text and two colons::

  Literal block

**Result**:

 Paragraph with no space between text and two colons::

  Literal block
