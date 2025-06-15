=====================
Searching and Finding
=====================

Entering search queries
=======================

To start a search, enter a query into the short query input field and type
enter or click the search icon. By default, the names, summary, tags, content, namengram,
summaryngram, and contentngram fields of each item's last revisions are searched.
Deleted items (trash) are excluded.

The search results view provides a form for refining the search through
ajax updates. Click the `More Search Options` link to see the form.
A transaction is started each time a character is added or removed
in the search field. If keying is rapid, it is possible that results will
processed out of order. The `Whoosh query` shows the last term processed.

Clicking the Search Options link displays alternatives for modifying the search.
Ajax updates will be made whenever a radio button or checkbox is changed.

Below the search form is the query processed by Whoosh, and Whoosh generated
suggestions for additional searches by input, item name, and item content.

Finally, the search hits are presented. These are ordered by
the whoosh scoring number. Each hit will contain the item name and some
meta data. If available, the item summary and partial item content with the
search term highlighted will be shown.

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

Explicit alternative (does the same as above)::

  wiki AND moin

Search for documents containing "wiki" OR "moin"::

  wiki OR moin

Search for documents containing "wiki" and NOT "bad"::

  wiki NOT bad

Explicit alternative (does the same as above)::

  wiki AND NOT bad

Group terms using ()::

  wiki AND NOT (bad OR worse)

Redirect to best match
======================

If you know the target item name, start the search term with a back-slash character.
Only the names and namengram fields will be searched. If there is a hit, the browser will be
redirected to the highest scoring hit.

Examples
--------
Search for a specific item name and immediately redirect browser to best match::

  \Home
  \Home/subitem
  \users/JoeDoe

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

See https://en.wikipedia.org/wiki/Regular_expression for basics about regexes.

See https://docs.python.org/3/library/re.html about python's regex implementation,
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


Searching an item's subitems
============================
To limit the search to an item's sub-items, use a leading `>`, followed by the
item's name, followed by the search arguments.

Examples
--------
Wild cards, regular expressions, etc. may be used in the search arguments::

  >colors blue
  >users/JohnDoe red*
  >home red OR blue OR green

Searching in specific fields
============================

If not specified otherwise, moin will search in ``names``,
``tags``, ``summary``, ``comment`` and ``content`` fields. Three fields with
n-gram support are also searched by default: ``namengram``, ``summaryngram``
and ``contentngram``.

N-gram indexing is a powerful method for getting fast, “search as you type” functionality.
A tokinizer splits words within ngram content fields into strings of 3 to 6 characters.
These small strings may be matched against search terms that are tokinized into strings
of 3 to 6 characters.

To specify the field to search in, just use the `fieldname:searchterm` syntax.
If embedded spaces are desired then do: `fieldname:"search term"`. Separate
multiple terms with a space: `content:foo tags:Foo` is the same as
`content:foo AND tags:Foo`.

The following table includes fields that may be useful for searching.

+-------------------------+-------------------------------------------------------+
| Field name              | Field value                                           |
+-------------------------+-------------------------------------------------------+
| ``acl`` **              | access control list (see below)                       |
+-------------------------+-------------------------------------------------------+
| ``address``             | submitter IP address, e.g. 127.0.0.1                  |
+-------------------------+-------------------------------------------------------+
| ``comment``             | editor comment on save, rename, etc.                  |
+-------------------------+-------------------------------------------------------+
| ``content``             | document contents, e.g. This is some example content. |
+-------------------------+-------------------------------------------------------+
| ``contentngram`` **     | document contents, tokenized by 3 to 6 characters.    |
+-------------------------+-------------------------------------------------------+
| ``contenttype``         | document type: text, image, audio, moinwiki, jpg, ... |
+-------------------------+-------------------------------------------------------+
| ``itemlinks`` **        | link targets of the document, e.g. OtherItem          |
+-------------------------+-------------------------------------------------------+
| ``itemtransclusions`` **| transclusion targets of the document, e.g. OtherItem  |
+-------------------------+-------------------------------------------------------+
| ``language``            | (main) language of the document contents, e.g. en     |
+-------------------------+-------------------------------------------------------+
| ``mtime``               | document modification (submission) date, 2011-08-07   |
+-------------------------+-------------------------------------------------------+
| ``namengram`` **        | document names, tokenized by 3 to 6 characters.       |
+-------------------------+-------------------------------------------------------+
| ``names``               | document names, e.g. Home, MyWikiPage                 |
+-------------------------+-------------------------------------------------------+
| ``namespace``           | namespace:"" for default or namespace:users           |
+-------------------------+-------------------------------------------------------+
| ``name_exact``          | same as ``name``, but is not tokenized                |
+-------------------------+-------------------------------------------------------+
| ``name_old``            | name_old:* for all renamed items                      |
+-------------------------+-------------------------------------------------------+
| ``summary``             | summary text, if provided by author                   |
+-------------------------+-------------------------------------------------------+
| ``summaryngram`` **     | summary text, tokenized by 3 to 6 characters.         |
+-------------------------+-------------------------------------------------------+
| ``tags``                | tags of the document, e.g. important, hard, todo      |
+-------------------------+-------------------------------------------------------+
| ``username``            | submitter user name, e.g. JoeDoe                      |
+-------------------------+-------------------------------------------------------+

** These fields exist only in the current revisions index, see Notes below.

Examples
--------
Search in metadata fields::

  contenttype:text
  contenttype:image/jpeg
  tags:todo
  mtime:2022-01-08  # use ISO 8601 dates, not time; `mtime:2022-01 works
  address:127.0.0.1
  username:JoeDoe

Search items with an item ACL that explicitly gives Joe read rights::

  acl:Joe:+read

Notes
=====

There are two indexes. The smaller index is used by default. It only indexes the
current revision of each item. The larger index is used when the `All` radio
button under the Search Options link is selected. The larger indexes all
revisions of all items including revisions of deleted items. As noted in the table
above the larger index omits several fields to save space.

By default, all namespaces are searched, including the userprofiles index. Because
the userprofiles index is normally read restricted, hits will be blocked and included
as `n items are not shown because read permission was denied` at the bottom of the page.

Items with transcluded content do not contain the transcluded content within the
item's index. An item containing "foo" within its content and trancluding an item with
"bar" within its content cannot be matched by searching for "foo AND bar". Both items
will be matched by searching for "foo OR bar".

Moin only uses an indexed search. Keep in mind that this has some special properties:

 * By using an index, the search is fast
 * Because it is only using an index, it can only find what was put there
 * If you use wildcards or regexes, it will still use the index, but in a different, slower way

For example:

 * create an item with "FooBar" in the name, content, summary, tag, and comment fields
 * search for "ooba" - the namengram, summaryngram, and contentngram will match
 * search for "FooBar": names, namengram, tags, summary, summaryngram, content,
   contentngram, and comment will match
 * search for "foobar":  names, namengram, summary, summaryngram, content, contentngram,
   and comment will match

More information
================

See the `Whoosh query language docs <https://whoosh.readthedocs.io/en/latest/querylang.html>`_.
