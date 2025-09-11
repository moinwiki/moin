===========
Maintenance
===========

Reduce Revisions
================

This process removes all but the current revision of selected items,
it reduces the storage required for your wiki at the expense of loss
of history.

To perform on the entire wiki, run the following command::

 moin maint-reduce-revisions

To perform on an item named "ItemName", run the following command::

 moin maint-reduce-revisions -q ItemName

Set Metadata
============

Manually modify item metadata.

.. _validate-metadata:

Validate and Optionally Fix Metadata
====================================

Modifications of wiki data outside of edits via the web app,
such as using the load-help and item-put moin commands,
can result in invalid metadata.

The processes below check for and optionally fix the following issues:

* size does not match the size of the revision's data in bytes
* SHA1 hash does not match the hash of the revision's data
* parent id should not be present for revision number 1 of a given item
* parent id for each revision should be the data id for the previous revision number for that item
* every revision should have a revision number
* an item should not have repeated revision numbers

To check for invalid metadata, run the following command::

 moin maint-validate-metadata --all-backends

To view a detailed list of invalid items::

 moin maint-validate-metadata --all-backends --verbose

To fix issues, add the ``--fix`` option to any of the above commands.

To operate on only a selection of backends, replace the ``--all-backends`` option with ``--backends``,
followed by a comma-separated list of backends to process.
