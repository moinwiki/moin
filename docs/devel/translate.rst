====================
Translating MoinMoin
====================

If your language already exists
-------------------------------

To find out if someone has already started a translation of moin2 into your
language; check the folder moin/translations in the source tree.
If there is a folder with your language code (locale) [#]_, you can
start with the steps below. If not, please take a look at `If your
language doesn't exist yet`_.


1. Make sure you have the latest version of the source tree (git).
   You will also need to have python installed, with setuptools and babel
   packages.

2. Go to the top directory and execute::

       pybabel update -l <locale> -i src/moin/translations/MoinMoin.pot \
               -d src/moin/translations/ -w 116

   where locale is the short language descriptor of your desired
   language. It should be the name of a folder in MoinMoin/translations.
   For German it is "de".

3. Open the file ``src/moin/translations/<locale>/LC_MESSAGES/messages.po``
   and do your translation. A short explanation of this process follows:

   * Find an entry with an empty or bad translated text, the text after
     msgstr, and apply your changes.

   * **never** edit the 'msgid' string, and only edit the 'msgstr' field

   * Variables like ``%(name)x``, where x is any character, must be kept as
     they are. They must occur in the translated text.

   * For better readability you can divide a text-string over more than
     one line, by "surrounding" each line with double quotes (").
     It is a usual convention to have a maximal line-length of 80
     characters.

   * Comments starting with "#.", "*#:*" or "*#|*" are
     auto-generated and should not be modified.

   * Comments starting with "# " (# and at least one whitespace) are
     translator-comments. You can modify/add them. They have to be
     placed right before the auto-generated comments.

   * Comments starting with "*#,*" and separated with "," are flags.
     They can be auto-generated, but they can also be set by the
     translator.

     An important flag is "fuzzy". It shows that the msgstr string might
     not be a correct translation. Only the translator can
     judge if the translation requires further modification, or is
     acceptable as it is. Once satisfied with the translation, he/she then
     removes this fuzzy attribute.

4. Save the messages.po file and execute::

       pybabel compile -l <locale> -d src/moin/translations/


Guidelines for translators
``````````````````````````
In languages where a separate polite form of address exists, like the
German "Sie"/"Du", always use the polite form.


If your language doesn't exist yet
----------------------------------

You want to translate moin2 to your language? Great! Get in contact with
the developers, but ...

.. note::

  please don't ask us whether we want other translations, we
  currently do not want them, it is still too early. We just want
  1 translation and it needs to be German because that is what many
  moin developers can maintain themselves.

1. Initialize a new catalog::

       pybabel init -l <locale> -i src/moin/translations/MoinMoin.pot \
               -d src/moin/translations/ -w 116

2. Adjust the ``src/moin/translations/<locale>/LC_MESSAGES/messages.po``.

   Follow the instructions in `First steps with a new *.po file`_ and
   then you can remove the fuzzy flag, which prevents the file from
   being compiled.

3. Follow the steps above, see `If your language already exists`_.

First steps with a new ``*.po`` file
````````````````````````````````````

A newly created translation needs a few initial preparations:

* replace "``PROJECT``" with "``MoinMoin 2``"

* replace "``FIRST AUTHOR <EMAIL@ADDRESS>``" with the appropriate information
  about yourself

* replace "``PROJECT VERSION``" in the head msgstr with
  "``MoinMoin 2.0``" or newer if neccessary

* change the value of "``Last-Translator``" to your data

* change the value of "``Language-Team``" to
  "``Language <moin-user@lists.sourceforge.net>``"

Note for developers
-------------------

We use the ``format()``-Method in internationalized Strings, e.g.
``_('Hello {name}').format(name='World')``. ``_()`` is an alias for ``gettext()``

If the translatable string contains a variable plural, that means
the string contains an object whose exact number you don't know,
you will have to use ``N_()``, which is an alias for ``ngettext()``.
Note that this is not only needed for the decision
between one and more objects, because other languages have other
and more difficult plurals than English. The usage is
``N_(singular, plural, num).format(**variables)``. ``**variables``
are used to substitute the keys by ``format()`` as explained above.

Example:
``N_('{number} file removed from {directory}', '{number} files removed from {directory}', num=n).format(number=n, directory=directory)``

``n`` has to appear twice because the first gives ngettext() information
about the exact number and the second is the variable for the format
string replacement.

If you made changes to any gettext() string, please update the .pot file
using::

    pybabel extract -F babel.cfg -o src/moin/translations/MoinMoin.pot \
            -k "_ gettext L_ lazy_gettext N_ ngettext" \
            --msgid-bugs-address "English <moin-user@python.org>" \
            --copyright-holder "Moin Core Team, see http://moinmo.in/MoinCoreTeamGroup" \
            --project "moin" --version "<version>" -w 116 src/

Because this sometimes creates large diffs, just because of a
change in line numbers, you can of course use this command sparingly.
Another option for better readability is to do a separate commit
for this.


------

.. [#] For more information on locale strings, see
   https://www.gnu.org/software/gettext/manual/html_node/Locale-Names.html.
