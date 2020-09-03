=======================
Templates and Meta Data
=======================

Two features that are related to the creation, editing and saving of an
item are templates and meta data.

Templates
=========

Templates make it easier for users to add new items that repeat a
heading structure or phrases that are similar to many other items.
Instead of starting from scratch or using a copy, paste, delete, type
new data; templates can be created that have the common
text and structure already completed. A template page must have a
tag of "template".

When creating a new item, users can save time and possibly eliminate
errors by choosing a template from a list of applicable templates.
Only templates having the same content type and namespace as the new item
will be shown as choices.

For templates with the MoinWiki markup, Predefined Variables can be used to insert
date, time, user name, item name, and others.

Meta Data
=========

When an item is edited (including non-text items like images, etc.),
most themes provide a means of updating certain meta data
associated with the item. The meta data fields that may be updated by
all editors include Summary, Tags, and Names.

Users with admin authority on the item may update the item's ACLs.
The format of ACL rules is discussed within the configuration section under
authorization.

Most themes will display the Summary field above the item's content. The
use of this field is optional. When used, it may contain a one-line
summary of the pages content, a TODO list of additional content that
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
History, will show all item names in a single row. Other reports which are
sorted by name, such as Index and Tags, will show each name in a separate
row.
