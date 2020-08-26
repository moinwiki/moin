=====================
Searching and Finding
=====================

Entering search queries
=======================

To start a search, enter a query in the short query input field and type
enter or click the search icon. By default, the name, summary, tag and
content indexes for the latest revisions of all items will be searched.

The search results view provides a form for refining the search through
ajax updates. A transaction is started each time a character is added to
the search field or a checkbox is clicked.

Below the search form is the query processed by whoosh, suggestions for
additional searches by item name, and suggestions for additional
searches by item content.

And finally, the search hits are presented. By default these are ordered by
the whoosh scoring number. Each hit will contain the item name, some
meta data, item summary if available, and partial item content with the
search term highlighted.

Simple search queries
=====================
Just enter one or more words into the query input field and hit ``Enter``.

If your query consists of multiple words, it will only find documents containing ALL those
words. You can use AND, OR, NOT to refine your search. "AND" is the default.

Examples
--------
Search for "wiki"::

  wiki

Search for documents containing "wiki" AND "moin"::

  wiki moin

  or (does the same):

  wiki AND moin

Search for documents containing "wiki" OR "moin"::

  wiki OR moin

Search for documents containing "wiki" and NOT "bad"::

  wiki NOT bad

Using wildcards
===============

If you want to enter word fragments or if you are not sure about spelling or
word form, you can use wildcards for the parts you do not know:

+----------------+-----------------------------------+
| Wildcard       | Matches                           |
+----------------+-----------------------------------+
| ``?``          | one arbitrary character           |
+----------------+-----------------------------------+
| ``*``          | any count of arbitrary characters |
+----------------+-----------------------------------+

Examples
--------
Search for something like wiki, wika, wikb, ...::

  wik?

Search for something like wiki, willi, wi, ...::

  w*i

You can also use it for poor man's language independent word stemming.

Matches on clean, cleaner, cleanest, cleaning, ...::

  clean*

Using regular expressions
=========================

Regular expressions enable even more flexibility for specifying search terms.

See http://en.wikipedia.org/wiki/Regular_expression for basics about regexes.

See http://docs.python.org/library/re.html about python's regex implementation,
which we use for MoinMoin.

You need to use this syntax when entering regexes: r"yourregex"

Examples
--------
Search for hello or hallo::

  r"h[ae]llo"

Search for words starting with foo::

  r"^foo"
  r"\Afoo"

Search for something like wiki, wika, wikb, ...::

  r"wik."

Search for something like wiki, willi, wi, ...::

  r"w.*i"


Searching in specific fields
============================

As long as you do not specify otherwise, moin will search in ``name``,
``name_exact`` and ``content`` fields.

To specify the field to search in, just use the `fieldname:searchterm` syntax.

+-----------------------+-------------------------------------------------------+
| Field name            | Field value                                           |
+-----------------------+-------------------------------------------------------+
| ``wikiname``          | wiki name, e.g. ITWiki, EngineeringWiki, SalesWiki    |
+-----------------------+-------------------------------------------------------+
| ``name``              | document name, e.g. Home, MyWikiPage                  |
+-----------------------+-------------------------------------------------------+
| ``name_exact``        | same as ``name``, but is not tokenized                |
+-----------------------+-------------------------------------------------------+
| ``content``           | document contents, e.g. This is some example content. |
+-----------------------+-------------------------------------------------------+
| ``contenttype``       | document type, e.g. text/plain;charset=utf-8          |
+-----------------------+-------------------------------------------------------+
| ``tags``              | tags of the document, e.g. important, hard, todo      |
+-----------------------+-------------------------------------------------------+
| ``summary``           | summary text, if provided by author                   |
+-----------------------+-------------------------------------------------------+
| ``language``          | (main) language of the document contents, e.g. en     |
+-----------------------+-------------------------------------------------------+
| ``mtime``             | document modification (submission) time, 201112312359 |
+-----------------------+-------------------------------------------------------+
| ``username``          | submitter user name, e.g. JoeDoe                      |
+-----------------------+-------------------------------------------------------+
| ``address``           | submitter IP address, e.g. 127.0.0.1                  |
+-----------------------+-------------------------------------------------------+
| ``hostname``          | submitter DNS name, e.g. foo.example.org              |
+-----------------------+-------------------------------------------------------+
| ``acl``               | access control list (see below)                       |
+-----------------------+-------------------------------------------------------+
| ``itemlinks``         | link targets of the document, e.g. OtherItem          |
+-----------------------+-------------------------------------------------------+
| ``itemtransclusions`` | transclusion targets of the document, e.g. OtherItem  |
+-----------------------+-------------------------------------------------------+

Examples
--------
Search in metadata fields::

  contenttype:text
  contenttype:image/jpeg
  tags:todo
  mtime:201108
  address:127.0.0.1
  language:en
  hostname:localhost

Search items with an item ACL that explicitly gives Joe read rights::

  acl:Joe:+read

Limiting search to a specific wiki, for example in a wiki farm's shared index::

  wikiname:SomeWiki

Notes
=====
moin uses indexed search. Keep in mind that this has some special properties:

 * By using an index, the search is usually rather fast
 * Because it is only using an index, it can only find what was put there
 * If you use wildcards or regexes, it will still use the index, but in a different, slower way

For example:

 * "foobar" is put into the index somehow
 * you search for "ooba" - you will not find it, because only "foobar" was put into the index
 * solution: search for "foobar": fast and will find it
 * solution: search for "*ooba*" or r".*ooba.*": slow, but will find it

More information
================

See the `Whoosh query language docs <https://whoosh.readthedocs.io/en/latest/querylang.html>`_.
