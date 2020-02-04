If you are reading this, it probably means you have successfully installed
moin2 on your local PC or laptop and are interested in creating a website
using https://www.pythonanywhere.com.

If you have existing data you want to save, take backups.


STEP 1 - Update local repo

To start, make sure your local moin repo is up to date by doing a "git pull".
Then load all the files in the /moin/contrib/pythonanywhere directory
into your favorite text editor (one of the files is this file).


STEP 2 - Get an account

If you have not already done so, head over to https://www.pythonanywhere.com,
maybe read some help pages, open a free or paid account, and confirm your
email address.

Note that if you have a free account, you will exceed the CPU seconds
threshold during installation and will be placed in the "tarpit". The
installation process will run slowly during the later steps but
will eventually complete.


STEP 2A - If there is an old moin installation, delete it

If you have a broken moinmoin2 installation or a Python 2.7 installation
that you want to convert to Python 3, then choose the Web tab on the
pythonanywhere dashboard, scroll to the bottom of the page and click the red
"Delete <AccountName>@.pythonanywhere.com" button. Next, click the Files tab and
delete the old moin/ and moin-venv-pythonx.x/ directories.


STEP 3 - Install moin2

Find your way to the pythonanywhere Dashboard, and click the Consoles link.
Click on the Bash link to start a Bash console. You cannot paste into the bash
console so you must type all the commands.

It may help to open
https://moin-20.readthedocs.io/en/latest/admin/install.html#downloading-and-installing
in a separate browser window or tab. Follow the installation guide:

    git clone https://github.com/moinwiki/moin
    cd moin
    python3.7 quickinstall.py  # or any later version
    ./m extras
    ./m docs
    ./m sample

Do not attempt to run the built-in server (./m run). Because pythonanywhere
is an external web server, the appropriate section of the moin docs is here:
https://moin-20.readthedocs.io/en/latest/admin/serve.html#external-web-server-advanced

If you are not a Python programmer and expert web master, the above reference
is not helpful. Don't panic, more specific instructions for pythonanywhere are
shown below.


STEP 4A - Perform PythonAnywhere manual confiuration

Get get your web browser back to the Dashboard:

    https://www.pythonanywhere.com/user/<AccountName>/

Near upper right, click on the "Web" link which should get you to:

    https://www.pythonanywhere.com/user/<AccountName>/webapps/#tab_id_<AccountName>_pythonanywhere_com

Next, at the top left of the page, there is a blue button labeled
"+ Add a new web app:". Click it.

On the pop up labeled "Your web app's domain name", click the Next button in
the lower right.

On the popup labeled "Select a Python Web framework" click
"Manual configuration".

On the popup labeled "Select a Python version" select "Python 3.7"
(or later version).

On the "Manual Configuration" popup, click "Next" near lower right. That
should bring you to:

    https://www.pythonanywhere.com/user/<AccountName>/webapps/#tab_id_<AccountName>_pythonanywhere_com

Scroll down to about the middle of the page to the section labeled "Code"
and edit the section so it looks similar to this, after replacing <AccountName>
with your account name:

    Code:

    What your site is running.
    Source code:                  /home/<AccountName>/moin/src/moin

    Working directory:            /home/<AccountName>/moin

    WSGI configuration file:      /var/www/<AccountName>_pythonanywhere_com_wsgi.py

    Python version:               3.7


    Virtualenv:

    -- snip 3 lines --

    /home/<AccountName>/moin-venv-python3.7/


STEP 4B - Replace the default _pythonanywhere_com_wsgi.py

Click the WSGI configuration file link:
"/var/www/<AccountName>_pythonanywhere_com_wsgi.cpy"

Keep the browser window open as you view the file contents. Switch to your
favorite file editor that has the file named _pythonanywhere_com_wsgi.py
that you loaded from ../moin/contrib/pythonanywhere/. Copy and paste
the contents of that file into the browser window replacing all the old
code with a few lines of new code. Click the Save button near the upper right.


STEP 4C - Upload wsgi.py file

Click the hamburger symbol (3 horizontal bars) in the upper right and select
"Files" in the dropdown. On the files page click the "moin/" link on the left
side center. You are in the right place if the last file in the /moin/
directory is wikiconfig.py.

On the bottom of the page, click the yellow button labeled "Upload a file".
On the file dialog box, navigate to your local copy of the
../moin/contrib/pythonanywhere/ directory and select the wsgi.py file,
click the "Open" button. When the upload is complete you should see the
wsgi.py file above the yellow "Upload a file" button.


STEP 5 - Reload server and view Home page

Near the top right of the web page, click the "Web" button. Click the green
"Reload <AccountName>.pythonanywhere.com" button.

When the reload is complete, click the link to <AccountName>.pythonanywhere.com
that is located just above the green button.

If all is well, you should see the sample Home page. Next secure your wiki
from unwanted hackers. See /contrib/wikiconfig/ contents. Reload the server after
making any changes.


STEP 5 - Troubleshooting

If you get the dreaded
    "Something went wrong :-("
page, review the instructions to insure all steps were completed successfully.

If the problem persists, post the bottom content of the
"<AccountName>.pythonanywhere.com.error.log".
