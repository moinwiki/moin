# Copyright: 2023 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - import content and user data from a moin 1.9 compatible storage into the moin2 storage.
"""

from moin.utils.tree import moin_page


# a dict of (content_type -> migration_callback)
_migration_callbacks = {}


def migrate_macros(dom):
    """Walk the DOM tree and call known migration functions

    While walking the DOM tree any element of a content type
    with a matching migration callback function will be passed
    to that same function for manipulation (i.e. migration).

    :param dom: the tree to check for elements to migrate
    :type dom: emeraldtree.tree.Element
    """

    for node in dom.iter_elements_tree():
        if node.tag.name == "part" or node.tag.name == "inline-part":

            # if a callback is registered for this content type
            # let it manipulate the DOM node
            if node.get(moin_page.content_type) in _migration_callbacks:
                _migration_callbacks[node.get(moin_page.content_type)](node)


def register_macro_migration(content_type, migration_callback):
    """Register callback for migrating elements of a certain content type

    Once registered, the migration will walk the DOM tree and use the callback
    function to manipulate elements of the given content type for migration.

    :param content_type: content type that shall be passed to the callback
                         for conversion, e.g. x-moin/macro;name=My19MacroName
    :type content_type: str
    :param migration_callback: conversion function that manipulates
                               the DOM element in-place
    :type migration_callback: function(emeraldtree.tree.Element) -> None
    """
    if content_type not in _migration_callbacks:
        _migration_callbacks[content_type] = migration_callback
