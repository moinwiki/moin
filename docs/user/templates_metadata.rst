======================
Templates and Metadata
======================

Two features that are related to the creation, editing, and saving of an
item are templates and metadata.

Templates
=========

Templates make it easier for users to create new items that
are similar to many other items.
Instead of starting from scratch or using a copy, paste, and modify technique,
templates that contain the common text and structure can be created. A
template item must have a tag of "template".

When creating a new item, if there are available templates for
the selected content type and namespace, then an extra step is added to the
create item dialog that allows the editor to choose a template. If a template is selected, the
content of the template item will be loaded and copied to the
modify screen's textarea.

To create a new template, just create an item and add a tag of "template"
before saving the item. Once created, each user creating a new item in the
target namespace and content type will be given the option of using any
of the available templates.

Templates may define data for the ACL, Summary, and Tags fields. These values
will be copied to the modify form within the item creation dialog; note the `template`
tag will not be copied. Users wanting to create a new template using an old
template will need to re-enter the `template` tag.

For templates with Moin Wiki markup, Predefined Variables can be used to insert
date, time, username, item name, and others. See Predefined Variables
in the Moin Wiki markup overview.

The example below is a very simple template for the **users** namespace. Each user
is encouraged to create a home page using the 4-line Moin Wiki markup template.
**@ITEM@** and **@EMAIL@** are predefined variables and will be replaced with
the item name (the new item name is expected to be the user's name) and the user's
email address (copied from the current user's settings) when the item is saved.
To create a home page, each user begins the creation of a new item in the **users** namespace,
selects the template, enters a nickname and hobbies, and saves the item.::

    = @ITEM@ =
    Nickname:
    Hobbies:
    Email: @EMAIL@


Metadata
=========

When an item is edited (including non-text items like images, etc.),
most themes provide a means of updating certain metadata
associated with the item. The metadata fields that may be updated by
all editors include Summary, Tags, and Names.

Users with admin authority on the item may update the item's ACLs.
The format of ACL rules is discussed within the configuration section under
authorization.

Most themes will display the Summary field above the item's content. The
use of this field is optional. When used, it may contain a one-line
summary of the page's content, a TODO list of additional content that
should be added or verified, or other special instructions to future readers
and editors.

For fields that may have multiple entries like the Tags and Names fields,
use commas to separate the entries. Leading and trailing spaces are stripped,
embedded spaces will become part of the tag or name.

Tags provide an alternate means of indexing articles. While tags are frequently
used to group items based on the item's subject matter, they can also
be used to group items in ways unrelated to the subject matter such as
marking items that need additional content, editing, review, etc. Most themes
provide a link to a Tags view within the navigation panel.

While most items will have a single name, item editors may add or delete
multiple names. Editors may find multiple names useful when renaming or
merging items. Item names cannot span multiple namespaces. Most themes
will show all item names within the Page Trail panel. Some reports, such as
History, will show all item names in a single row. Other reports that are
sorted by name, such as Index and Tags, will show each name in a separate
row.
