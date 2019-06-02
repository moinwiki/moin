If you are reading this, it probably means you have successfully installed moin2
on your local PC or laptop and are interested in creating a website using
http://www.pythonanywhere.com.

To start, make sure your local moin repo is up to date by doing a "git pull".
Then load all the files in the /moin/contrib/pythonanywhere directory
into your favorite text editor.

If you have not already done so, head over to http://www.pythonanywhere.com,
maybe read some help pages, open a free (or paid) account, and confirm your
email address.

Note that if you have a free account, you will exceed the CPU seconds
threshold during installation and will be placed in the "tarpit". The
installation process will likely run slowly during the later steps.

Find your way to the pythonanywhere Dashboard, and click the Consoles link.
Click on the Bash link to start a Bash console.

It may help to open
https://moin-20.readthedocs.io/en/latest/admin/install.html#downloading-and-installing
in a separate browser window or tab. Follow the installation guide:

    git clone https://github.com/moinwiki/moin
    cd moin
    python quickinstall.py
    ./m extras
    ./m docs
    ./m sample

Do not attempt to run the built-in server (./m run). Because pythonanywhere is an
external web server, the appropriate section of the moin docs is here:
https://moin-20.readthedocs.io/en/latest/admin/serve.html#external-web-server-advanced

If you are not a Python programmer and expert web master, the above reference is not
helpful. Don't panic, more specific instructions for pythonanywhere are shown below.


<< REPLACE MoinMoin2 with YOUR pythonanywhere account name in the steps below: >>

First, get get your web browser back to the Dashboard:

    https://www.pythonanywhere.com/user/MoinMoin2/

Near upper right, click on the "Web" link which should get you to:

    https://www.pythonanywhere.com/user/MoinMoin2/webapps/#tab_id_moinmoin2_pythonanywhere_com

If the page says "You have no web apps" skip the remainder of this paragraph. Otherwise,
scroll to the bottom of the page and click the red "Delete moinmoin2.pythonanywhere.com"
button. If you have a paid account and are running several apps, be careful, do not delete
the wrong app.

Next, at the top left of the page, there is a blue button labeled
"+ Add a new web app:". Click it.

On the pop up labeled "Your web app's domain name", click the Next button in the lower right.

On the popup labeled "Select a Python Web framework" click "Manual configuration".

On the popup labeled "Select a Python version" select "Python 2.7".

On the "Manual Configuration" popup, click Next near lower right. That should bring you here:

    https://www.pythonanywhere.com/user/MoinMoin2/webapps/#tab_id_moinmoin2_pythonanywhere_com

Scroll down to about the middle of the page to the section labeled "Code".

It is easiest to start with working directory, click the /home/MoinMoin2/ link and add
"moin" to the end, then click the check box. The link should be "/home/MoinMoin2/moin"

Next, opposite Source code, click the "Enter the path to your web app source code".
Type in "/home/MoinMoin2/moin/src/moin". Click the check box.

Next, down a few lines under the Virtualenv section, add a virtual env:
"/home/MoinMoin2/moin-venv-python".

The code and Virtual env sections should look similar to:

    Code:

    What your site is running.
    Source code:                  /home/MoinMoin2/moin/src/moin

    Working directory:            /home/MoinMoin2/moin

    WSGI configuration file:      /var/www/moinmoin2_pythonanywhere_com_wsgi.py

    Python version:               2.7


    Virtualenv:

    -- snip --

    /home/MoinMoin2/moin-venv-python


Next, go back to the Code section, click the WSGI configuration file link:
"/var/www/moinmoin2_pythonanywhere_com_wsgi.cpy"

You should see the file contents. keep the browser window open. Switch to your favorite file
editor that has the file named _pythonanywhere_com_wsgi.py loaded. Copy and paste the
contents of this file into the browser window replacing everything. There should be 12 lines
of code. Click the Save button near the upper right.

Click the hamburger symbol (3 horizontal bars) in the upper right and select Files in the
dropdown. On the files page click the "moin/" link on the left side center. You are in the
right place if the last file in the /moin/ directory is wikiconfig.py.

On the bottom of the page, click the yellow button labeled "Upload a file". On the file dialog
box, navigate to your local copy of the .../moin/contrib/pythonanywhere/ directory and select
the wsgi.py file, click the Open button. When the upload is complete you should see the
wsgi.py file above the yellow "Upload a file" button.

Near the top right of the web page, click the "Web" button. Click the green
"Reload MonMoin2.pythonanywhere.com" button.

When the reload is complete, click the link to MoinMoin2.pythonanywhere.com that is
located just above the green button.

If all is well, you should see the sample Home page. Next secure your wiki from
unwanted hackers. See /contrib/wikiconfig/ contents.

If you get the dreaded "Something went wrong :-(" page post the contents of
"moinmoin2.pythonanywhere.com.error.log".


Help wanted, fix this if there are errors or better methods.
