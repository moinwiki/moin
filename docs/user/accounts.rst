=============
User Accounts
=============

Accounts provide an easy way for wiki users to identify themselves to MoinMoin, store personal
preferences and track wiki contributions. Account creation is simple and straight forward, and
provides many benefits over browsing and editing anonymously.

Account Creation
================

To create an account, click the :guilabel:`Login` button at the top of the page. You will be taken to a login
page allowing you to either log in or create an account. Proceed to the create account page
by clicking the account creation button, and you will be presented with an account creation form.
The fields of this form are as follows:

Name
 Your username on the wiki. Will appear in the history section of any wiki item which you edit. This is a required field.

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

OpenID
 This is an optional field where you may enter an OpenID to be associated with your account. OpenID
 provides a common mechanism for websites to authenticate users and store data about them like
 username and real name. If you have an OpenID, you may want to enter it here.

.. note::
 Some wikis require email verification, in which case you will have click an activation link which
 will be sent to the email address you provide. You must complete this step before you start using
 the wiki.

User Settings
=============

User settings provide a way for to customise your MoinMoin experience and perform account
maintenance functions like changing email address or password. To access your settings page, click
the :guilabel:`Settings` button at the top of the page.

The settings page appears as a list of links to various sub-pages for changing elements of your
wiki experience, each of these sub-pages are listed below:

Personal Settings
-----------------

Personal settings include wiki language and locale, username, alias and OpenID.

Name
 Your username, as it will appear on the wiki and in the history pages of wiki items which you edit.

Alias-Name
 The alias name can be used to override your username, so you will still log in using your username
 but your alias name will be displayed to other users and in your history page.

OpenID
 If you have an OpenID which you would like to associate with your account, enter it here.

.. warning::
 **MOINTODO** Leaving the OpenID field blank gives a warning saying "This OpenID is already in use"

Timezone
 Setting this value will allow you to see edit times as they would appear in your time zone. For
 example, an edit time of 10AM UTC would appear as 8PM AEST if you changed your time zone to 
 GMT +10/Australian Eastern Standard Time.

Locale
 Your preferred language for interacting with MoinMoin.

Change Password
---------------

Password changes are recommended if you believe that the password you are using has been put into
the hands of an untrusted third party.

Current Password
 Enter the password which you currently use to log into the wiki. This prevents passersby from
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

Editor Size
 The size (in lines) of MoinMoin's plain text editor when you edit an item.

.. warning::
 **MOINTODO** "Editor Size" isn't a very good title as it doesn't specify *which* editor or in what 
 units the size is. This setting doesn't seem to affect my MoinMoin instance, either.

History results per page
 The number of edits you will see when you look at the history of an item.

Navigation Settings
-------------------

.. warning::
 **MOINTODO** This page is blank. Perhaps it should be removed?

Options
-------

.. warning::
 **MOINTODO** "Options" isn't a very good name. Aren't they all "options"? The settings in the
 options page don't seem to be grouped in any particular category, either. Perhaps these options
 should be moved to another settings page?

The "Options" section allows you to control privacy and advanced features of MoinMoin.

Publish my email (not my wiki homepage) in author info
 Control whether or not other wiki users may see your email address.

Open editor on double click
 This option allows you to simply double click the text on any MoinMoin item and have it opened
 in the editor.

Show comment sections
 Show the comment sections for wiki items you view.

Disable this account forever
 Tick this box if you want to delete your account forever. **This action is permanent, do not
 delete your account unless you really need to.**

Your User Page
==============

You user page is a wiki space in which you may share information about yourself with other users of
that wiki. It can be accessed by clicking the button with your username on it at the top of the
screen, and is edited like a normal wiki item.

Logging out
===========

.. warning::
 **MOINTODO** Currently logging out just removes the user's session cookie. These cookies remain
 valid after logging out (and even after a password change), and could be used to impersonate a
 user. See BitBucket issue #94.

Logging out of your account can prevent account hijacking on untrusted or insecure computers, and is
considered best practice for security. To log out, click the :guilabel:`Logout` button at the top
of the page. You will be redirected to a page confirming that you have logged out successfully.
