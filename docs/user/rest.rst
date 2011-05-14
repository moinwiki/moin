===============================
ReST (ReStructured Text) Markup
===============================

The report gives reST syntax documentation. The structure and order has been matched with other markup rst files namely creolewiki.rst and mediawiki.rst at http://hg.moinmo.in/moin/2.0-dev/file/42d8cde592fb/docs/user

Features currently not working with moin's Wiki parser are marked with **RSTTODO**.

Features currently not working with moin's sphinx setup are marked with **SPHINXTODO**.


**SPHINXTODO CSS**, the tables seem to have missing borders despite of the fact that the rst markup is correct.

Headings
========

Rather than imposing a fixed number and order of section title adornment styles, the order enforced will be the order as encountered.
The first style encountered will be an outermost title (like HTML H1), the second style will be a subtitle, the third will be a subsubtitle, and so on.

**Markup**: ::

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

**Notes** The underline below the title must at least be equal to the length of the title itself.

Text formatting
===============

The following is a table of inline markup that can be used to control text formatting in Moin.

+-------------------------------------+---------------------------------------+
| Markup                              | Result                                |
+=====================================+=======================================+
| ``**Bold Text**``                   | **Bold text**                         |
+-------------------------------------+---------------------------------------+
| ``*Italic*``                        | *Italic*                              |
+-------------------------------------+---------------------------------------+
| ````Inline Literals````             | ``Inline Literals``                   |
+-------------------------------------+---------------------------------------+

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

 .. image:: example.png

**Result**:

 .. image:: example.png
 
**Note** **RSTTODO** everything after an image markup is shown as a comment in moin2.
 
Blockquotes and Indentations
============================

Every additional space before the first word in a line will add an indent before the line.

**Markup**: ::

 indented text
  text indented to the 2nd level

**Result**:

 indented text
  text indented to the 2nd level

**Markup**: ::

  This is an ordinary paragraph, introducing a block quote.

    "It is my business to know things.  That is my trade."

    -- Sherlock Holmes

**Result**:

  This is an ordinary paragraph, introducing a block quote.

    "It is my business to know things.  That is my trade."

    -- Sherlock Holmes

**Notes**
 - A block quote may end with an attribution: a text block beginning with "--", "---", or a true em-dash, flush left within the block quote.
 - **RSTTODO** the attribution does not work in moin2.

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
 
   1. item 1.1
   
   2. item 1.2
   
 2. item 2

**Result**:

 1. item 1
 
   1. item 1.1
   
   2. item 1.2
   
 2. item 2
   
**Notes**:
 - The order and the numbering agent have to be maintained by user. Any thing can be used to number the items (e.g. a/A or i/I).
 - **SPHINXTODO** sphinx will remove the first space before every list item.
 - even the base level item has to have a space in the beginning

Definition Lists
================

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
 
**Note** **RSTTODO** C does not extend fully upto the end of D.

Admonitions
===========

Admonitions are used as a caution/notification block.

**Markup**: ::
 
 .. note:: This is a paragraph
 
**Result**:

 .. note:: This is a paragraph

Comments
========

Comments are not shown on the page but depending on the output formatter, they might be included as HTML comments (``<!-- -->``).

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

Literal blocks are used to show test as-is. i.e no markup processing is done within a literal block. A minimum (1) indentation is required for the text block to be recognized as a literal block.

**Markup**: ::

 Paragraph with a space between succeeding two colons ::

  Literal block
 
**Result**:

 Paragraph with a space between succeeding two colons ::

  Literal block
  
**Markup**: ::

 Paragraph with no space between succeeding two colons::

  Literal block
 
**Result**:

 Paragraph with no space between succeeding  two colons::

  Literal block

