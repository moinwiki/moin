========
Features
========
We recommend trying out moin rather than reading feature lists.
But in case you need it nevertheless, here it is:

Operating System Support
========================
Moin is implemented in Python and that is a platform independant language.
So it'll work on Linux, Mac OS X, Windows (and others).

That said, Linux is the preferred and most tested deployment platform and
likely having less issues than e.g. Windows.

Servers
=======
* Builtin Python server (from werkzeug) - easy to use, just start it.
* Any server that talks WSGI to moin:

  - Apache2 with mod_wsgi
  - IIS with isapi-wsgi
  - Other WSGI servers, see http://wsgi.org/

* With the help of flup middleware about any other server speaking:

  - fastcgi
  - scgi
  - ajp
  - cgi (slow, not recommended)

Authentication
==============
* Builtin (username / password login form of moin, MoinAuth)
* Builtin HTTP Basic Auth (browser login form, HTTPAuthMoin)
* OpenID (relying party, OpenIDAuth)
* Auth against LDAP / Active Directory (LDAPAuth)
* Any authentication your web server supports (via GivenAuth)

Authorization
=============
* Content Access Control Lists (ACLs)

  - global (per storage backend)
  - local (per wiki item)
  - give rights like:

    + create,destroy
    + read,write,rename
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
* we store data of any type (text, images, audio, binary)
* we separately store any metadata
* everything is revisioned
* all important metadata is indexed

Storage Backend Types
---------------------
* file system
* sql database
* Mercurial DVCS
* you can add your own backend

Serialization
-------------
* dump backend contents to xml
* load backend contents from xml

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
* Global History for all items ("Recent Changes")
* Local History for one item ("History")
* Diffs between any revision

  + text item diffs (rendered nicely with html)
  + image diffs
  + binary "diff" (same or not same)
* Tags / Tag Cloud
* Missing Items
* Orphaned Items
* "What refers here?" functionality
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
* by email (smtp or sendmail)

Translation / Localization
--------------------------
* currently English and German translations only (this is intended until the
  code and the texts are more stable)
* any localization (provided by babel / pytz)

Logging
=======
* Flexible logging provided by `logging` module of python stdlib

Technologies
============
* html5, css, javascript with jquery, svg
* python
* flask, flask-cache, flask-babel, flask-themes, flask-script
* werkzeug, pygments, flatland, blinker, babel, emeraldtree, sqlalchemy, sqlite
* optional: mercurial, postgresql, mysql


