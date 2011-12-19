=====================
Searching and Finding
=====================

Entering search queries
=======================

Usually there is a simple but rather short search query input field offered by
the theme - by submiting a query it will search in item names and
content (but only in the current stuff, not in non-current revisions) and display
the search results to you.

On the search results view you will get a bigger search query input field
(e.g. for refining your query) and you may also choose to additionally search
in non-current item revisions (selecting that will search in all
revisions).

Simple search queries
=====================
Just enter one or more words into the query input field and hit ``Enter``.

If your query consists of multiple words, it will only find documents containing ALL those
words ("AND" is the default).

You can use AND (default), OR, NOT to refine your search.

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

You can also use it for poor man's language independant word stemming.

Matches on clean, cleaner, cleanest, cleaning, ...::

  clean*

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
| ``language``          | (main) language of the document contents, e.g. en     |
+-----------------------+-------------------------------------------------------+
| ``mtime``             | document modification (submission) time, 201112312359 |
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

Limiting search to a specific wiki (in a wiki farm's shared index)::

  wikiname:SomeWiki

Notes
=====
moin uses indexed search - keep in mind that this has some special properties:

 * By using an index, the search is rather usually fast 
 * Because it is only using an index, it can only find what was put there
 * If you use wildcards, it will still use the index, but in a different, slower way

E.g.:

 * "foobar" is put into the index somehow
 * you search for "ooba" - you will not find it, because only "foobar" was put into the index
 * solution: search for "foobar" - fast and will find it
 * solution: search for "*ooba*" - slow, but will find it

More infos
==========

See the `Whoosh query language docs <http://packages.python.org/Whoosh/querylang.html>`_.

