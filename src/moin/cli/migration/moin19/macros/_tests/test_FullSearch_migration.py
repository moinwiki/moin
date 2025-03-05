# Copyright: 2025 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.cli.migration.moin19.macros Test FullSearch
"""

import pytest

from moin.converters.moinwiki19_in import ConverterFormat19

from moin.cli.migration.moin19 import import19
from moin.cli.migration.moin19.macro_migration import migrate_macros

from moin.utils.tree import moin_page


@pytest.mark.parametrize(
    "legacy_macro,expected_args",
    [
        ("<<FullSearch(CategorySample)>>", 'item="/", tag="CategorySample"'),
        ("<<FullSearch(category:CategorySample)>>", 'item="/", tag="CategorySample"'),
        ("<<FullSearchCached(CategoryTest)>>", 'item="/", tag="CategoryTest"'),
    ],
)
def test_macro_conversion_itemlist(legacy_macro, expected_args):
    # macro calls for Categories
    converter = ConverterFormat19()
    dom = converter(legacy_macro, import19.CONTENTTYPE_MOINWIKI)
    migrate_macros(dom)  # in-place conversion

    body = list(dom)[0]
    part = list(body)[0]

    assert part.get(moin_page.content_type) == "x-moin/macro;name=ItemList"
    assert part.get(moin_page.alt) == f"<<ItemList({expected_args})>>"


@pytest.mark.parametrize(
    "legacy_macro,expected_args",
    [
        ("<<FullSearch()>>", ""),
        ("<<FullSearch(Calendar/2025-01-01)>>", "Calendar/2025-01-01"),
        ("<<FullSearch('AnyText')>>", "'AnyText'"),
    ],
)
def test_macro_conversion_fullsearch(legacy_macro, expected_args):
    # macro calls other than Categories are not changed
    converter = ConverterFormat19()
    dom = converter(legacy_macro, import19.CONTENTTYPE_MOINWIKI)
    migrate_macros(dom)  # in-place conversion

    body = list(dom)[0]
    part = list(body)[0]

    assert part.get(moin_page.content_type) == "x-moin/macro;name=FullSearch"
    assert part.get(moin_page.alt) == f"<<FullSearch({expected_args})>>"
