:orphan:

.. _glossary:

Glossary
========

.. glossary::
   :sorted:

   acl
      Access Control List - you can use it to specify who may do what in
      your wiki.

   contenttype
      A formal, standardized way of specifying the type of some data.
      For example, 'text/plain;charset=UTF-8' is the contenttype for a simple piece
      of text (encoded using UTF-8), and 'image/png' is the contenttype
      for a PNG image.

   item
      A generic, revisioned object stored in your wiki storage.

   revision
      Part of an item's history, has metadata and data created for this item
      at some specific time in its history. If you create an item, you create
      its first revision. If you edit it and save, you create its next
      revision.

   data
      Just the raw data, no more, no less; it can be text, an image, or a PDF.

   metadata
      Additional information related to or about some data. For example, if
      you create a new PDF item revision, the revision data will be the PDF
      file's content, but Moin will also store revision metadata
      that indicates this revision is a PDF (its contenttype - we do not
      rely on or require a .pdf extension in the item name), when it was saved,
      any comment you provided when saving, etc.

   session
      As the protocol (HTTP) used by web browsers is stateless, a way
      to keep state is needed. This is usually done by using a cookie stored
      in the user's browser. It is used, for example, to stay logged in to your
      user account, to store the trail of items you visited, and for easier
      navigation.

   wiki engine
      Software used to run a wiki site.

   wiki farm
      Running multiple wikis together on one server. Often, there is some
      shared, common configuration inherited by all wikis, so each
      individual wiki's configuration becomes rather small.

   wiki instance
      All configuration and data related to a single wiki.

   wiki item
      A single content item within a wiki site.

   wiki page
      A single content item within a wiki site, possibly used for text-like items.

   wiki site
      A web site implemented using a wiki engine.

   WSGI
      Web Server Gateway Interface. It is a specification for how web servers,
      such as Apache with mod_wsgi, communicate with web applications, such as
      MoinMoin. It is a Python standard, described in detail in PEP 333.

   emeraldtree
      An XML/tree processing library used by Moin.

   flask
      A microframework used by Moin.

   jinja
      A templating engine used by Moin (Jinja2).

   sqlalchemy
      An SQL database abstraction library used by Moin (SQLAlchemy).

   sqlite
      An easy-to-use SQL database used by Moin (SQLite).

   werkzeug
      A WSGI library used by Moin (Werkzeug).
