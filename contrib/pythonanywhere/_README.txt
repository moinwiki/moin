To add a moin2 web application to pythonanywhere.com,
see: https://help.pythonanywhere.com/pages/WebAppBasics
and (many) other help pages.

When creating the web app, choose "Manual Configuration".

A wsgi file named:
    /var/www/(your name>_pythonanywhere_com_wsgi.py
will be created automatically.

Replace the entire contents of the above file with the contents of:
    _pythonanywhere_com_wsgi.py

Upload the wsgi.py file to the /moin/ directory (the directory with
wikiconfig.py in it).

Reload your web app, and point your browser to your web site.

Help wanted, fix this if there are errors or better ways.
