=========
Searching
=========
Entering search queries
=======================

Usually there is a simple and rather short search query input field offered by the theme - if you submit a query from there, it will only search the current item revisions and show the related results to you.

On that search results view, you will get a bigger search query input field (e.g. for refining your query) and you may also choose to additionally search in non-current revision item revisions (selecting that will search in all revisions).

Simple search queries
=====================
Just enter one or few simple words.

If you give multiple words, it will only find documents containing ALL those words (``AND`` is the default).

You can use ``AND`` (default), ``OR``, ``NOT`` to refine your search.

Examples
--------
::

    # search for "wiki"
    wiki

    # search for documents containing "wiki" AND "moin"
    wiki moin
    # this does the same:
    wiki AND moin
    # search for documents containing "wiki" OR "moin"
    wiki OR moin
    # search for documents containing "wiki" and NOT "bad"
    wiki NOT bad


Wildcard queries
----------------
If you want to enter word fragments or if you are not sure about spelling or word form, use wildcards for the parts you do not know:
 * ``?`` matches 1 arbitrary character
 * ``*`` matches multiple arbitrary characters.

Examples
--------
::

    # would match on wiki, wika, wikb, ...
    wik?
    # would match on wiki, willi, wi, ...
    w*i

    # you can also use it for poor man's language independant stemming:
    # matches on wash, washes, washing, washed, ...
    wash*


Searching in specific fields
----------------------------

As long as you do not specify otherwise, moin will search in ``name``, ``name_exact`` and ``content`` fields.

To specify the field to search in, just use the `fieldname:searchterm` syntax.

Examples
--------
::

    # search in metadata fields
    contenttype:text
    contenttype:image/jpeg
    tags:demo
    mtime:201108
    address:127.0.0.1
    language:en 
    hostname:localhost

    # search items with item ACL that explicitly gives Joe read rights
    acl:Joe:+read

    # limiting search to a specific wiki in a wiki farm index
    wikiname:SomeWiki


Notes
-----
moin uses indexed search - keep in mind that this has some special properties:
 * as it is using an index, it is rather fast usually
 * because it is only using the index, it can only find what was put there
 * if you use wildcards, it will still use the index, but in a different, slower way

E.g.:
 * ``foobar`` is put into the index somehow
 * you search for "ooba" - you will not find it, because only ``foobar`` was put into the index
 * solution: search for ``foobar`` - fast and will find it
 * solution: search for ``*ooba*`` - slow, but will find it

More infos
----------

`Whoosh docs about its default query language <http://packages.python.org/Whoosh/querylang.html>`_
