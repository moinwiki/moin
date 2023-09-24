.. role:: bolditalic

===============
Markdown Markup
===============

This page introduces you to the most important elements of the Markdown syntax.
For details on the Python implementation of Markdown see https://python-markdown.github.io/

In addition to being supported by moin2, the Markdown markup language is used by issue trackers
such as those found in Bitbucket and Github. So what you learn here can be used there also.

.. _para3:

Features currently not working with moin's Markdown parser are marked with **MDTODO**.

This page, describing the Markdown syntax, is written in reST. Instances where reST cannot
duplicate the same rendering produced by Markdown are flagged with **reST NOTE**.
The reST parser used by Moin and the parser used by Sphinx are different. As noted below there
are several instances where one works and the other fails.

Table of Contents
=================

The table of contents is a supported extension that is distributed with Python Markdown.

**Markup**: ::

    [TOC]

**Result**:

.. contents::

Headings
========

Level 1 and 2 headings may be created by underlining with = and - characters, respectively.

Having equal numbers of characters in the heading and the underline
looks best in raw text, but having fewer or more = or - characters also works.

Heading levels 3 through 6 must be defined by prefixing the heading with a variable number of # characters indicating the heading level.  Heading levels 1 and 2 may be defined in the same manner. It is customary, but not required, to follow the # characters with a single space character. Another option is to append the appropriate number of # characters after the heading text.

**Markup**: ::

    Level 1
    =======

    # Level 1

    Level 2
    -------

    ## Level 2

    ### Level 3

    #### Level 4

    ##### Level 5

    ###### Level 6 ######


**Result**:

Level 3
-------

Level 4
*******

Level 5
:::::::

Level 6
+++++++

**NOTE**: Levels 1 and 2 are not shown above to avoid adding
unwanted entries to the table of contents. See the top of this page
for an approximate view of a level 1 heading and next section heading
below for level 2.

Preformatted Code
=================

To show a preformatted block of code, indent all the lines by 4 or more spaces.

**Markup**: ::

 Begin preformatted code

    First line
    Second line
        Third line

 End of preformatted code


**Result**:

Begin preformatted code ::

    First line
    Second line
        Third line

End of preformatted code

Simple text editing
===================

**Markup**: ::

    Paragraphs are separated
    by a blank line.

    To create a line break, end a line
    with 2 spaces.

    Use asterisk characters to create text attributes: *italic*, **bold**, ***bold italics***.
    Or, do the same with underscores: _Italics_, __bold__, ___bold italics___.
    Use backticks to create `monospace`.


**Result**:

Paragraphs are separated
by a blank line.

| To create a line break, end a line
| with 2 spaces.

Use asterisk characters to create text attributes: *italic*, **bold**, :bolditalic:`bold italics`.
Or, do the same with underscores: *Italics*, **bold**, :bolditalic:`bold italics`.
Use backticks to create ``monospace``.

**reST Note**: The moin reST parser will indent the second paragraph above.

Linking
=======

Markdown supports two style of links: inline and reference.

Inline Links
------------

Inline links use the form: ::

    [link text](url "optional title")

===========================================   ===============================================
 **Markup**                                    **Result**
===========================================   ===============================================
 [home page](Home)                             `home page <http:Home>`_
 [home item](Home "my home page")              `home item <http:Home>`_
 [a sub item](Home/subitem)                    `a sub item <http:Home/subitem>`_
 [toc1](markdown#table-of-contents)            `toc1 <http:markdown#table-of-contents>`_
 [toc2](#table-of-contents)                    `toc2 <http:#table-of-contents>`_
 [moinmoin](https://moinmo.in "Go there")      `moinmoin <https://moinmo.in>`_
 [![Image name](png)](Home "click me")         `png image <http:Home>`_
===========================================   ===============================================

**reST NOTE**: Links with title attributes and images as links are not supported in reST.
The internal links above are broken.

Wikilinks
---------

Wikilinks use the form: ::

    [[PageName]]

===========================================   ===============================================
 **Markup**                                    **Result**
===========================================   ===============================================
 [[Page]]                                      `Page <http:Page>`_
 [[Page/Subpage]]                              `Subpage <http:Page/Subpage>`_
===========================================   ===============================================

This features uses the `mdx_wikilink_plus <https://github.com/neurobin/mdx_wikilink_plus>`_ extension.

Reference Links
---------------

Reference links have two parts. Somewhere in the document the link label
is defined using a unique id; this has no visible output. Then the
reference link uses a form with square brackets rather than parens: ::

    [id]: url "optional title"

    [link text] [id]

===========================================   ==========================================
 **Markup**                                    **Result**
===========================================   ==========================================
 [apple]: https://www.apple.com/
 [MoinMoin]: https://moinmo.in/ "go!"
 [see apples][apple]                           `see apples <https://www.apple.com>`_
 [go to MoinMoin][MoinMoin]                    `go to MoinMoin <https://moinmo.in>`_
===========================================   ==========================================

**reST NOTE**: Links with title attributes are not supported in reST.

Lists
=====

Unordered lists may use `*`, +, or - characters as bullets.  The character used as a bullet does not effect the display.  The display would be the same if `*` characters were used everywhere.

**Markup**: ::

    * apples
    * oranges
    * pears
        - carrot
        - beet
            + man
            + woman
        - turnip
    * cherries

**Result**:

* apples
* oranges
* pears

    - carrot
    - beet

        + man
        + woman

    - turnip

* cherries

**reST NOTE**: As shown above and below, the Sphinx rendering of ordered
and unordered lists shows excessive spacing between levels.

Ordered lists use numbers and are incremented in regular order. Neither
alpha characters nor roman numerals are supported. Although you may use
numbers other than 1 with no adverse effect (as shown below), it is a
best practice to always start a list with 1.

**Markup**: ::

    1. apples
    1. oranges
    7. pears
        1. carrot
        1. beet
            1. man
            1. woman
        1. turnip
    1. cherries


**Result**:

 1. apples
 #. oranges
 #. pears

    1. carrot
    #. beet

        1. man
        #. woman

    #. turnip

 #. cherries

Lists composed of long paragraphs are easier to read in raw text if the
lines are manually wrapped with **optional** hanging indents. If multiple
paragraphs are required, separate the paragraphs with blank lines and indent.

**Markup**: ::

    *   Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
        Aliquam hendrerit mi posuere lectus. Vestibulum enim wisi,
        viverra nec, fringilla in, laoreet vitae, risus.
    *   Donec sit amet nisl. Aliquam semper ipsum sit amet velit.
        Suspendisse id sem consectetuer libero luctus adipiscing.
    *   Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
    Aliquam hendrerit mi posuere lectus. Vestibulum enim wisi,
    viverra nec, fringilla in, laoreet vitae, risus.
    *   Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
    Aliquam hendrerit mi posuere lectus. Vestibulum enim wisi,
    viverra nec, fringilla in, laoreet vitae, risus.
    *   Donec sit amet nisl. Aliquam semper ipsum sit amet velit.
    Suspendisse id sem consectetuer libero luctus adipiscing.


**Result**:

 -   Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
     Aliquam hendrerit mi posuere lectus. Vestibulum enim wisi,
     viverra nec, fringilla in, laoreet vitae, risus.
 -   Donec sit amet nisl. Aliquam semper ipsum sit amet velit.
     Suspendisse id sem consectetuer libero luctus adipiscing.
 -   Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
     Aliquam hendrerit mi posuere lectus. Vestibulum enim wisi,
     viverra nec, fringilla in, laoreet vitae, risus.
 -   Lorem ipsum dolor sit amet, consectetuer adipiscing elit.
     Aliquam hendrerit mi posuere lectus. Vestibulum enim wisi,
     viverra nec, fringilla in, laoreet vitae, risus.
 -   Donec sit amet nisl. Aliquam semper ipsum sit amet velit.
     Suspendisse id sem consectetuer libero luctus adipiscing.

Horizontal Rules
================

To create horizontal rules, use 3 or more -, `*`, or _ on a line.
Neither changing the character nor increasing the number of characters
will change the width of the rule.
Putting spaces between the characters also works.

**Markup**: ::

    ---

    text

    - - - - - -

    more text

    ******

    more text

    ______


**Result**:

----

text

-----

more text

******

more text

______


Backslash Escapes
=================

Sometimes there is a need to use special characters as literal characters, but Markdown's syntax gets in the way.  Use the backslash character as an escape.

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

**reST NOTE**: The Moin reST parser flags the use of 333 as a bullet number.


Nested Blockquotes
==================

Advanced blockquotes with nesting are created by starting a line with a > character.

**Markup**: ::

    > A standard blockquote is indented
    > > A nested blockquote is indented more
    > > > You can nest to any depth.


**Result**:

    A standard blockquote is indented
        A nested blockquote is indented more
            You can nest to any depth.

Images
======

Images are similar to links with both an inline and a reference style,
but they start with an exclamation point. Within Markdown, there is no
syntax to change the default sizes or positions of transclusions:

**Markup**: ::

    To transclude image from local wiki:
    ![Alt text 1](png "Optional title")

    Reference-style, where "logo" is a name defined anywhere within this item:
    ![Alt text 2][logo]

    Image references are defined using syntax identical to link references and
    do not appear in the rendered HTML:
    [logo]: png  "Optional title attribute"

    To transclude image from remote site:
    ![remote image](http://static.moinmo.in/logos/moinmoin.png)

**Result**:

To transclude image from local wiki:

.. image:: png
   :alt: Alt text 1
   :align: right

Reference-style, where "logo" is a name defined anywhere within this item:

.. image:: png
   :alt: Alt text 2
   :align: right

Image references are defined using syntax identical to link references and
do not appear in the rendered HTML:

To transclude image from remote site:

.. image:: http://static.moinmo.in/logos/moinmoin.png
   :alt: remote image
   :align: right

**reST NOTE**: The Moin reST parser renders all three images above. The
Sphinx parser renders only the external png image from
http://static.moinmo.in/logos/moinmoin.png. reST syntax does not allow the
rendering of inline images, nor the use of a title attribute. The logos
above are floated right, in Markdown the logos would appear as inline images.

Inline HTML
===========

**Note:** Use of the style attribute within HTML tags is dependent
upon configuration settings. See configuration docs for information on
`allow_style_attributes`.

You may embed a small subset of HTML tags directly into your markdown documents. ::

    <a>              - hyperlink.
    <b>              - bold, use as last resort <h1>-<h3>, <em>, and <strong> are preferred.
    <blockquote>     - specifies a section that is quoted from another source.
    <code>           - defines a piece of computer code.
    <del>            - delete, used to indicate modifications.
    <dd>             - describes the item in a <dl> description list.
    <dl>             - description list.
    <dt>             - title of an item in a <dl> description list.
    <em>             - emphasized.
    <h1>, <h2>, <h3> - headings.
    <i>              - italic.
    <img>            - specifies an image tag.
    <kbd>            - shows keyboard input.
    <li>             - list item in an ordered list <ol> or an unordered list <ul>.
    <ol>             - ordered list.
    <p>              - paragraph.
    <pre>            - pre-element displayed in a fixed width font and unchanged line breaks.
    <s>              - strikethrough.
    <sup>            - superscript text appears 1/2 character above the baseline used for footnotes and other formatting.
    <sub>            - subscript appears 1/2 character below the baseline.
    <strong>         - defines important text.
    <strike>         - strikethrough is deprecated, use <del> instead.
    <ul>             - unordered list.
    <br>             - line break.
    <hr>             - defines a thematic change in the content, usually via a horizontal line.

**Markup**: ::

    E = MC<sup>2</sup>

    This word is <b>bold</b>.

    This word is <em>italic</em>.

    This word is <strong>bold</strong>.

    This word is <strong style="color:red;background-color:yellow">bold</strong>;
    colors depend upon configuration settings.

**Result**:

|inlinehtml|

.. |inlinehtml| raw:: html

    E = MC<sup>2</sup><br><br>

    This word is <b>bold</b>.<br><br>

    This word is <em>italic</em>.<br><br>

    This word is <strong>bold</strong>.<br><br>

    This word is <strong style="color:red;background-color:yellow">bold</strong>;
    colors depend upon configuration settings.

reST NOTE: The moin reST parser will flag the above as an error because it
does not support the `raw` directive.

Extensions
==========

In addition to the TOC extension shown near the top of this page, the following features are installed as part of the "extras" extension.


Tables
------

All tables must have one heading row. By default table headings are centered and table body cells are aligned left. Use a ":" character on the left, right or both sides of the heading-body separator to change the alignment. Changing the alignment changes both the heading and table body cells.

As shown in the second table below, use of outside borders and neat alignment of the cells do not effect the display. Markup within the table cells is supported.

**Markup**: ::

    |Tables            |Are            |Very  |Cool    |
    |------------------|:-------------:|-----:|:-------|
    |col 2 is          |centered       |$12   |Gloves  |
    |col 3 is          |right-aligned  |$1600 |Necklace|
    |col 4 is          |left-aligned   |$100  |Hat     |

    `Tables`            |*Are*            |Very  |Cool
    ------------|:-------------:|-----:|:-------
    `col 2 is`|*centered*|$12|Gloves
    `col 3 is`|*right-aligned*|$1600|Necklace
    `col 4 is`|*left-aligned*|$100|Hat


**Result**:

================== =============== ======== ==========
 Tables             Are             Very     Cool
================== =============== ======== ==========
 col 2 is           centered        $12      Gloves
 col 3 is           right-aligned   $1600    Necklace
 col 4 is           left-aligned    $100     Hat
================== =============== ======== ==========

================== ================= ======== ==========
 `Tables`           *Are*             Very     Cool
================== ================= ======== ==========
 `col 2 is`         *centered*        $12      Gloves
 `col 3 is`         *right-aligned*   $1600    Necklace
 `col 4 is`         *left-aligned*    $100     Hat
================== ================= ======== ==========


**reST NOTE**: reST does not support cell alignment.

Syntax Highlighting of Preformatted Code
----------------------------------------

A second way to create a block of preformatted code without indenting
every line is to wrap the block in triple backticks.

To highlight code syntax, wrap the code in triple backtick characters
and specify the language on the first line.  Many languages are supported.

**Markup**: ::

    ``` javascript
    var s = "JavaScript syntax highlighting";
    alert(s);
    ```

    ~~~ {python}
    def hello():
       print "Hello World!"
    ~~~

**Result**: ::

    var s = "JavaScript syntax highlighting";
    alert(s);

    def hello():
       print "Hello World!"

**reST NOTE**: reST supports some generic highlighting of indented blocks. The
Moin Markdown highlighting is more colorful and varies per language.

Fenced Code
-----------

Another way to display a block of preformatted code is to "fence" the code with lines starting with three ~ characters.

**Markup**: ::

    ~~~
    ddd
    eee
    fff
    ~~~

**Result**: ::

   ddd
   eee
   fff

Smart Strong
------------

The smart strong extension prevents words with embedded double underscores from being converted. e.g.
`double__underscore__words` is wanted, not `double`**underscore**`words`.

**Markup**: ::

    Text with double__underscore__words.

    __Strong__ still works.

    __this__works__too__.

**Result**:

Text with double__underscore__words.

**Strong** still works.

**this__works__too**.



Attribute Lists
---------------

**Markup**: ::

    A class of LawnGreen  (that will create a greenish background per a CSS rule) is
    added to this paragraph.
    {: class="LawnGreen "}

    A `{: #para3 }` id was added to the 3rd paragraph on this page,
    so [click to see 3rd paragraph](#para3).

**Result**:

|bgcolor|

.. |bgcolor| raw:: html

    <span style="background-color:lawnGreen ">
    A class of lawnGreen  (that will create a greenish background per a CSS rule) is
    added to this paragraph.</span>

A `{: #para3 }` id was added to the 3rd paragraph on this page,
so `click to see 3rd paragraph <http:#para3>`_.

reST NOTE: The moin reST parser will flag the first example above as an error because it
does not support the `raw` directive.

Definition Lists
----------------

**Markup**: ::

    Apple
    :   Pomaceous fruit of plants of the genus Malus in
        the family Rosaceae.
    :   An american computer company.

    Orange
    :   The fruit of an evergreen tree of the genus Citrus.

**Result**:

Apple
    Pomaceous fruit of plants of the genus Malus in the family Rosaceae.

    An american computer company.

Orange
    The fruit of an evergreen tree of the genus Citrus.

Footnotes
---------

The syntax for footnotes in Markdown is rather unique.[^unique] Place any unique label after the characters "[^"  and close the label with a "]". The footnote text may be placed after the reference on a new line using the label, followed by a ":", followed by the footnote text. All footnotes are placed at the bottom of the document under a horizontal rule in the order defined.

[^unique]: Markdown footnotes are unique.

**Markup**: ::

    Footnotes[^1] have a label[^label] and a definition[^!DEF].

    [^1]: This is a footnote
    [^label]: A footnote on "label"
    [^!DEF]: The footnote for definition

**Result**:

Footnotes [1]_ have a label [#label]_ and a definition [#DEF]_.

.. [1] This is a footnote

.. [#label] A footnote on "label"

.. [#DEF] The footnote for definition

Admonition
----------

The `Admonition extension <https://python-markdown.github.io/extensions/admonition/>`_ adds `rST-style <http://docutils.sourceforge.net/docs/ref/rst/directives.html#specific-admonitions>`_ admonitions to Markdown.

**Syntax**: ::

    !!! type "optional explicit title within double quotes"
        Any number of other indented markdown elements.

        This is the second paragraph.

If you don’t want a title, use a blank string "".

The following types are supported:

* attention
* caution
* danger
* error
* hint
* important
* note
* tip
* warning

**Markup**: ::

    !!! note
    You should note that the title will be automatically capitalized.

**Result**:

.. note::
   You should note that the title will be automatically capitalized.
