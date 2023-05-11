===========
Maintenance
===========

Reduce Revisions
================

This process removes all but the current revision of selected items,
it reduces the storage required for your wiki at the expense of loss
of history.

To perform on entire wiki, run the following command::

 moin maint-reduce-revisions

To perform on an item with name "ItemName", run the following command::

 moin maint-reduce-revisions -q ItemName

Set Metadata
=============

Manually modify metadata of items.

.. _validate-metadata:

Validate and Optionally Fix Metadata
====================================

Modifications of wiki data outside of edits via the webapp
such as use of the load-help and item-put moin commands
can result in invalid metadata.

The processes below check for and optionally fix the following issues:

* size does not match size of the revision's data in bytes
* sha1 hash does not match has of the revision's data
* revision numbers for an item's revision should make an unbroken sequence starting at 1
* parent id should not be present for revision number 1 of a given item
* parent id for each revision should be the data id for the previous revision number for that item

To check for invalid metadata, run the following command::

 moin maint-validate-metadata --all-backends

To view detailed list of invalid items::

 moin maint-validate-metadata --all-backends --verbose

To fix issues, take your wiki offline and add ``--fix`` option to any of the above commands.

To operate on only a selection of backends, replace ``--all--backends`` option with ``--backends``
followed by comma separated list of backends to process

If the ``--fix`` finds anything to fix, you must rebuild the index
with the newly created metadata, see :doc:`index`
