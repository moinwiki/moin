.. contents::


==================
Docbook XML Markup
==================


This page shows the different features of our native DocBook support. A table of contents is automatically
generated from section titles.

This content, describing the Docbook syntax, is written in reST. Instances where reST cannot
duplicate the same rendering produced by Docbook are flagged with **reST NOTE**.
The reST parser used by Moin and the parser used by Sphinx are different.


Lists
=====

Itemized List
-------------
**Markup:**::


  <itemizedlist>
    <listitem>
      <para>Item 1
      </para>
    </listitem>
    <listitem>
      <para>Item 2
      </para>
    </listitem>
    <listitem>
      <para> Item 3
      </para>
    </listitem>
  </itemizedlist>


**Results:**

* Item 1
* Item 2
* Item 3

Ordered List
------------

**Markup:**::


  <orderedlist numeration="lowerroman">
    <listitem>
      <para>One</para>
    </listitem>
    <listitem>
      <para>Two</para>
    </listitem>
    <listitem>
      <para>Three</para>
    </listitem>
    <listitem>
      <para>Four</para>
    </listitem>
  </orderedlist>


**Results:**

i. One

#. Two

#. Three

#. Four

**reST NOTE**: should show small roman numbers here


Simple text formatting
======================

**Markup:**::


  <para>
  <emphasis role="bold">This</emphasis> paragraph contains
  <emphasis>some <emphasis>emphasized</emphasis> text</emphasis>
  and a <superscript>super</superscript>script
  and a <subscript>sub</subscript>script.
  </para>


**Results:**
**This** paragraph contains
*some *emphasized* text*
and a \ :sup:`super`\ script
and a \ :sub:`sub`\ script.


Quotes
======

**Markup:**::

  <para>This software is provided <quote>as is</quote>, without expressed
  or implied warranty.
  </para>


**Results:**
This software is provided "as is", without expressed
or implied warranty.


Trademarks and Copyrights
=========================

**Markup:**::


  <para><trademark class='registered'>Nutshell Handbook</trademark> is a
  registered trademark of O'Reilly Media, Inc.
  </para><para>
  <trademark class="copyright">2014 Joe Doe</trademark>
  </para><para>
  <trademark class="trade">Foo Bar</trademark> is an unregistered trademark.
  </para><para>
  <trademark class="service">Foo Bar</trademark> is an unregistered servicemark.
  </para>


**Results:**
Nutshell Handbook® is a
registered trademark of O'Reilly Media, Inc.


© 2014 Joe Doe

Foo Bar™ is an unregistered trademark.


Foo Bar\ :sup:`SM`\  is an unregistered servicemark.


Preformatted Data
=================

**Markup:**::


  <screen><![CDATA[
  <para>
  My  preformatted      data.

  Remove blanks from "] ] >" below:
  </para>
  ] ] ></screen>


**Results:**::


  <para>
  My  preformatted      data.

  Remove blanks from "] ] >" below:
  </para>


Links
=====

**Markup:**::


  <link xlink:href="https://moinmo.in/">MoinMoin rocks</link>


**Results:**

`MoinMoin rocks <https://moinmo.in/>`_


Tables
======

**Markup:**::


  <table frame='all'><title>Sample Table</title>
  <tgroup cols='5' align='left' colsep='1' rowsep='1'>
  <colspec colname='c1'/>
  <colspec colname='c2'/>
  <colspec colname='c3'/>
  <colspec colnum='5' colname='c5'/>
  <thead>
  <row>
    <entry namest="c1" nameend="c2" morecols='1' align="center">Horizontal Span</entry>
    <entry>a3</entry>
    <entry>a4</entry>
    <entry>a5</entry>
  </row>
  </thead>
  <tfoot>
  <row>
    <entry>f1</entry>
    <entry>f2</entry>
    <entry>f3</entry>
    <entry>f4</entry>
    <entry>f5</entry>
  </row>
  </tfoot>
  <tbody>
  <row>
    <entry>b1</entry>
    <entry>b2</entry>
    <entry>b3</entry>
    <entry>b4</entry>
    <entry morerows='1' valign='middle'><para>  <!-- Pernicous Mixed Content -->
    Vertical Span</para></entry>
  </row>
  <row>
    <entry>c1</entry>
    <entry namest="c2" nameend="c3" morecols='1' align='center' morerows='1' valign='bottom'>Span Both</entry>
    <entry>c4</entry>
  </row>
  <row>
    <entry>d1</entry>
    <entry>d4</entry>
    <entry>d5</entry>
  </row>
  </tbody>
  </tgroup>
  </table>


**Results:**

+-----------------+-----+----+---------------+
| Horizontal Span | a3  | a4 | a5            |
+=====+===========+=====+====+===============+
| b1  | b2        | b3  | b4 |               |
+-----+-----------+-----+----+ Vertical Span |
| c1  |                 | c4 |               |
+-----+  Span Both      +----+---------------+
| d1  |                 | d4 | d5            |
+-----+-----------+-----+----+---------------+
| f1  | f2        | f3  | f4 | f5            |
+-----+-----------+-----+----+---------------+

**reST NOTE**: the table does not show the correct result.

Images
======

An "inlinemediaobject" may be positioned within a paragraph and aligned to the text top, middle, or bottom
through use of the align attribute.

**Markup:**::

  <para>
  Here is an image
  <inlinemediaobject>
    <imageobject>
      <imagedata format="png" align="middle" fileref="png"/>
    </imageobject><caption>My Logo</caption>
  </inlinemediaobject>
  embedded in a sentence.
  </para>


**Results:**

Here is an image

.. image:: png
   :height: 80
   :width: 100
   :scale: 50
   :alt: My Logo
   :align: center

embedded in a sentence.

**Notes:**
 - The Sphinx parser does not have an image named "png" so the alternate text
   will be displayed.
 - **reST NOTE**: There is no facility to embed an image within a paragraph.

Footnotes
=========

All footnotes are placed at the bottom of the document in the order defined.

**Markup:**::

  <para>An annual percentage rate (<abbrev>APR</abbrev>) of 13.9%<footnote>
  <para>The prime rate, as published in the Wall Street
  Journal on the first business day of the month,
  plus 7.0%.
  </para>
  </footnote>
  will be charged on all balances carried forward.
  </para>


**Results:**

An annual percentage rate (APR) of 13.9% [#]_ will be charged on all balances carried forward.


.. [#]
  The prime rate, as published in the Wall Street
  Journal on the first business day of the month,
  plus 7.0%.
