========
Features
========

Operating System Support
========================
Moin is implemented in Python, a platform-independent language.
It works on Linux, Mac OS X, Windows, FreeBSD and other OSes that support
Python.

That said, Linux is the preferred and most tested deployment platform and
will likely have fewer issues than, for example, Windows.

Servers
=======
* Builtin Python server from werkzeug, which is easy to use.
* Any server that talks WSGI to moin:

  - Apache2 with mod_wsgi
  - IIS with isapi-wsgi (not recommended - if you must use Windows, but have
    a choice concerning the web server, please use Apache2).
  - Other WSGI servers, see http://wsgi.org/

* With the help of flup middleware about any other server speaking:

  - fastcgi
  - scgi
  - ajp
  - cgi (slow, not recommended)

Authentication
==============
* Builtin - username / password login form of moin, MoinAuth
* Builtin HTTP Basic Auth - browser login form, HTTPAuthMoin
* OpenID - relying party, OpenIDAuth
* Auth against LDAP / Active Directory (LDAPAuth)
* Any authentication your web server supports via GivenAuth

Authorization
=============
* Content Access Control Lists (ACLs)

  - global, using a mapping, so you can apply ACLs on parts of the namespace
  - local, per wiki item
  - give rights, such as::

    + create, destroy
    + read, write, rename
    + admin

  - to:
   
    + specific users
    + specific groups of users
    + all logged-in users
    + all users

* Function ACLs

Anti-Spam
=========
* TextChas (text captchas)
* Form Ticketing

Storage
=======
Item Types
----------
* we store data of any type, such as text, images, audio, binary
* we separately store any metadata
* everything is revisioned

Storage Backend Types
---------------------
* file system
* sql database, such as sqlite3 or everything supported by SQLalchemy
* Kyoto Tycoon / Kyoto Cabinet
* you can easily add your own backend with little code

Serialization
-------------
* dump backend contents to a single file
* load backend contents from such a file

Search / Indexing
=================
* important metadata is indexed
* content data is converted (if possible) and indexed
* fast indexed search, fast internal operations
* flexible and powerful search queries
* search current and historical contents
* using a shared index, find content in any farm wiki

User Interface
==============
OO user interface
-----------------
* Most functionality is done in the same way no matter what type your wiki
  item has.

Templating
----------
* Theme support / User interface implemented with templates

Wiki features
-------------
* Global History for all items (full list)
* Latest Changes ("Recent Changes"), only lists the latest changes of an item
* Local History for one item ("History")
* Diffs between any revision

  + text item diffs, rendered nicely with html
  + image diffs
  + binary "diff" (same or not same)
* Tags / Tag Cloud
* Missing Items
* Orphaned Items
* "What refers here?" functionality
* "What did I contribute to?" functionality
* Sitemap
* Macro support

Markup support
--------------
* Moin Wiki
* Creole
* MediaWiki
* reST
* DocBook XML
* HTML
* plus code / text file highlighting for many formats

Feeds
-----
* Atom
* Google Sitemap

Notification
------------
* by email: smtp or sendmail

Translation / Localization
--------------------------
* currently English and German translations only; no others will be added until
  the code and texts for moin2 are more stable
* any localization, provided by babel / pytz

Logging
=======
* Flexible logging provided by `logging` module of python stdlib

Technologies
============
* html5, css, javascript with jquery, svg
* python
* flask, flask-cache, flask-babel, flask-themes, flask-script
* whoosh, werkzeug, pygments, flatland, blinker, babel, emeraldtree
* sqlalchemy (supports all popular SQL DBMS), sqlite, kyoto tycoon/cabinet

