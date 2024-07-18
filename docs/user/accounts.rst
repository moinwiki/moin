=============
User Accounts
=============

Accounts provide an easy way for wiki users to identify themselves to MoinMoin and other wiki users,
store personal preferences and track wiki contributions. Account creation is simple and
straightforward, and provides many benefits over browsing and editing anonymously.

Account Creation
================

To create an account, click the :guilabel:`Login` button at the top of the page. You will be taken to a login
page allowing you to either log in or create an account. Proceed to the create account page
by clicking the account creation button, and you will be presented with an account creation form.
The fields of this form are as follows:

Name
 Your username on the wiki.  Names must not contain "/",  ":", or "," characters, invisible unicode
 characters, or leading or trailing whitespace characters. Embedded single space characters
 are allowed.  This is a required field.

Password
 Your password for logging into your new account. Remember to pick a strong password with a mix
 of upper and lower case letters, numbers and symbols. This is also a required field.

Password
 Enter your new password again (same as the above field). This is a required field to make sure
 that your first password entry was correct.

E-Mail
 The email address which will be associated with your new account. This can be used by the wiki
 administrators to contact you or to verify your account if email verification is enabled on
 the wiki. This is a required field.

.. note::
 Some wikis require email verification, in which case you will have click an activation link which
 will be sent to the email address you provide. You must complete this step before you start using
 the wiki.

 Other wikis may limit new account creation to administrators only to prevent the creation
 of bogus accounts and spamming bots. In this case you will have to contact the administrator
 to request an account.

User Settings
=============

User settings provide a way for to customise your MoinMoin experience and perform account
maintenance functions like changing email address or password. To access your settings page, click
the :guilabel:`Settings` button at the top of the page.

The settings page appears as a list of links to various sub-pages for changing elements of your
wiki experience, each of these sub-pages are listed below:

Personal Settings
-----------------

Personal settings include wiki language and locale, name, alias and display-name.

Name
 Your username, as it will appear on the login form, the history pages of wiki items
 which you edit, and in the footer of items you have edited. All of these places will be
 rendered as links to your home page in the `users` namespace.
 If desired, name may be a comma separated list of names. For example, if it is tedious
 to type your long full name at login, you may create a short alias name: `JohnDoe, jd`.
 Alias names are only useful at login.

Display-Name
 If your wiki has a custom auth method that creates cryptic user names, then
 the display-name can be created as an alternative. You will still login using your username
 or alias. The display-name will appear as links in history pages and the footer of items you have edited.
 Use your display-name to create your home page in the users namespace.

Timezone
 Setting this value will display edit times converted to your local time zone. For
 example, an edit time of 10AM UTC would appear as 8PM AEST if you changed your time zone to
 GMT +10/Australian Eastern Standard Time.

Locale
 Your preferred language for interacting with MoinMoin. Edit dates and times are formatted based
 upon the locale unless the ISO 8601 option is selected under Options.

Change Password
---------------

Password changes are recommended if you believe that the password you are using has been compromised.

Current Password
 Enter the password which you currently use to log into the wiki. This prevents passers-by from
 changing the password of a logged in account. This is a required field.

New Password
 The new password which you would like to use. This is a required field.

New Password (repeat)
 Enter your new password again. Used to detect typographical errors. This is a required field.

Notification Settings
---------------------

Notification settings allow you to configure the way MoinMoin notifies you of changes and important
information.

E-Mail
 Change the email address MoinMoin sends emails to.

Wiki Appearance Settings
------------------------

Appearance settings allow you to customise the look and feel of the wiki.

Theme name
 The bundled MoinMoin wiki theme which you would like to use.

User CSS URL
 If you want to style MoinMoin with custom Cascading Style Sheets (CSS), enter a URL for your
 custom stylesheet here. Custom CSS provides an advanced level of control over appearance of
 MoinMoin pages.

Number rows in edit textarea
 The size (in lines) of MoinMoin's plain text editor when you edit an item. The default of 0
 resizes the textarea to hold the entire document being edited.

History results per page
 The number of edits you will see when you look at the history of an item.

Quick Links
-----------

Quick links enable users to add frequently referenced pages to the Navigation links. In most
cases, users will use the "Add Link" or "Remove Link" controls within Item Views to add or
remove quick links to local wiki items. Several different types of links may be added:

 - To manually add a link to a local wiki item, prefix the item name with the wiki name: MyWiki/myitem
 - To add a link to an external wiki page, use the wiki name as a prefix: MeatBall/RecentChanges
 - To add a link to an external web page, use the full URL, e.g.: https://moinmo.in
 - Other types of links, such as mailto: may be added


Options
-------

The "Options" section allows you to control privacy and advanced features of MoinMoin.

Always use ISO 8601 date-time format
 Display dates and times in ISO 8601 format rather than the usual Babel formats
 based upon the user's locale. If the UTC time zone is selected, dates and times
 will have a "z" suffix indicating the date or time is a UTC Zulu time.

Publish my email (not my wiki homepage) in author info
 Control whether or not other wiki users may see your email address.

Open editor on double click
 This option allows you to simply double click the text on any MoinMoin item and have it opened
 in the editor. When using the MoinMoin text editor, the textarea caret will be positioned on
 the paragraph that was clicked. If the textarea is larger than the display window, pressing the
 right-arrow key will scroll the page so the caret is visible near the bottom of the window.

Show comment sections
 Show the comment sections for wiki items you view.

Disable this account forever
 Tick this box if you want to disable your account. Your username or alias will still show in the
 history pages of items you have edited, but you will no longer be able to log in using your
 account.

Special Features for Users with Accounts
========================================

Your User Page
--------------

You user page is a wiki space in which you may share information about yourself with other users of
that wiki. It can be accessed by clicking the button with your username on it at the top of the
screen, and is edited like a normal wiki item.

"My Changes"
------------

To view your modifications to a wiki, click on ``User`` in the navigation area, then on ``My Changes``.
This will show a list of revisions you have made to wiki items sorted by date-time.

The first column will usually show an icon with a link to a diff showing the changes made at
that revision. If the item was deleted, the icon will have a link to a revert dialog. If the item
has only one revision, the icon will indicate the content type.

The second column will show the item name, aliases, or item ID (if the item was deleted)
at that revision with a link to a revision display.

The remaining columns with display timestamps, sizes, revision numbers, and comments.

Bookmarking
-----------

Some MoinMoin users spend a lot of time sifting through the global changes list (accessible via the
:guilabel:`History` button at the top of every MoinMoin page) looking for unread changes.
To help users remember which revisions they have read and which they have yet to read,
MoinMoin provides bookmarks. If you have read revisions up until the 13th of January, for example, you would
simply click the :guilabel:`Set bookmark` button next to the revisions from the 13th of January to hide
all revisions from before that date. If you wish to examine those revisions again, navigate back to the
global history page and click :guilabel:`Remove bookmark`.

Quicklinks
----------

At the top of every MoinMoin page, there is a row of buttons for quick access to commonly used MoinMoin
features like the global index, global history and homepage. Often, users need quick access to MoinMoin
items without having to search for them each time - quicklinks allow you to access your favourite wiki
items at the click of a button by placing links to them at the top of every page. To quicklink an item,
click the :guilabel:`Add Link` button at the top or bottom of a MoinMoin item. To remove a quicklink,
simply navigate back to the item and click the :guilabel:`Remove Link` button.

Quicklinks are associated with your account, so you will be able to access them from anywhere by simply
logging into the wiki.

Item Trail
----------

The item trail appears at the top of each page and lists previous items which you have visited. Users
with accounts may view this trail wherever they log in, whereas anonymous users have a different trail
on each computer that they visit.

Subscribing to Items
--------------------

Subscribing to items allows you to be notified via email when changes are made. To subscribe, navigate
to the item in question and click the :guilabel:`Subscribe` button at the top or bottom of the page. You
will now receive an email each time a user modifies this item. To unsubscribe, navigate to the item
again and click the :guilabel:`Unsubscribe` button at the top or bottom of the page.

Logging out
===========

Logging out of your account can prevent account hijacking on untrusted or insecure computers, and is
considered best practice for security. To log out, click the :guilabel:`Logout` button at the top
of the page. You will be redirected to a page confirming that you have logged out successfully.
