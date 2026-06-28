# Copyright: 2023 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - import content and user data from a Moin 1.9–compatible storage into the Moin 2 storage.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from moin.utils.tree import moin_page

if TYPE_CHECKING:
    from emeraldtree.tree import Element, Node

# A dict mapping content_type -> migration_callback.
_migration_callbacks: dict[str, Callable[[Node], None]] = {}


def migrate_macros(dom: Element) -> None:
    """Walk the DOM tree and call known migration functions.

    While walking the DOM tree, any element of a content type
    with a matching migration callback function will be passed
    to that same function for manipulation (i.e., migration).

    :param dom: The tree to check for elements to migrate.
    :type dom: emeraldtree.tree.Element
    """

    for node in dom.iter_elements_tree():
        if node.tag.name == "part" or node.tag.name == "inline-part":
            # If a callback is registered for this content type,
            # let it manipulate the DOM node.
            if node.get(moin_page.content_type) in _migration_callbacks:
                _migration_callbacks[node.get(moin_page.content_type)](node)


def register_macro_migration(content_type: str, migration_callback: Callable[[Node], None]) -> None:
    """Register a callback for migrating elements of a certain content type.

    Once registered, the migration will walk the DOM tree and use the callback
    function to manipulate elements of the given content type for migration.

    :param content_type: Content type that shall be passed to the callback
                         for conversion, e.g., x-moin/macro;name=My19MacroName
    :type content_type: str
    :param migration_callback: Conversion function that manipulates
                               the DOM element in-place.
    :type migration_callback: function(emeraldtree.tree.Element) -> None
    """
    if content_type not in _migration_callbacks:
        _migration_callbacks[content_type] = migration_callback
