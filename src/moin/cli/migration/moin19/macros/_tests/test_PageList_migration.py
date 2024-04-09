# Copyright: 2022 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.cli.migration.moin19.macros Test PageList
"""

import pytest

from moin.converters.moinwiki19_in import ConverterFormat19

from moin.cli.migration.moin19 import import19
from moin.cli.migration.moin19.macro_migration import migrate_macros
from moin.cli.migration.moin19.macros import PageList  # noqa

from moin.utils.tree import moin_page


@pytest.mark.parametrize(
    "legacy_macro,expected_args",
    [
        ("<<PageList>>", 'item=""'),
        ("<<PageList()>>", 'item=""'),
        ("<<PageList(regex:InterestingPage/*)>>", 'item="",regex="InterestingPage/*"'),
        ("<<PageList(Calendar/2014-08-22/)>>", 'item="",regex="Calendar/2014-08-22/"'),
        ("<<PageList(regex:SecondCalendar/2011[^/]*$)>>", 'item="",regex="SecondCalendar/2011[^/]*$"'),
        ("<<PageList(^WikiPageAboutRegularExpressions/*)>>", 'item="",regex="^WikiPageAboutRegularExpressions/*"'),
        ("<<PageList(regex:ArticleCollection/[^/]*)>>", 'item="",regex="ArticleCollection/[^/]*"'),
    ],
)
def test_macro_conversion(legacy_macro, expected_args):
    converter = ConverterFormat19()
    dom = converter(legacy_macro, import19.CONTENTTYPE_MOINWIKI)
    migrate_macros(dom)  # in-place conversion

    body = list(dom)[0]
    part = list(body)[0]

    assert part.get(moin_page.content_type) == "x-moin/macro;name=ItemList"
    assert part.get(moin_page.alt) == f"<<ItemList({expected_args})>>"

    if len(list(part)) > 0:
        arguments = list(part)[0]
        assert list(arguments)[0] == expected_args
