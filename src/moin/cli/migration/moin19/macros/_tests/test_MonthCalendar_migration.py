# Copyright: 2022 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.cli.migration.moin19.macros Test MonthCalendar
"""

import pytest

from moin.converters.moinwiki19_in import ConverterFormat19

from moin.cli.migration.moin19 import import19
from moin.cli.migration.moin19.macro_migration import migrate_macros
from moin.cli.migration.moin19.macros import MonthCalendar  # noqa

from moin.utils.tree import moin_page


@pytest.mark.parametrize(
    "legacy_macro,expected_args",
    [
        ("<<MonthCalendar()>>", ""),
        ("<<MonthCalendar('TestPage')>>", 'item="TestPage"'),
        (
            "<<MonthCalendar('TestPage',1995,3,2,,1,,)>>",
            'item="TestPage",year=1995,month=3,month_offset=2,fixed_height=true',
        ),
        (
            "<<MonthCalendar('CalendarOne*CalendarTwo',,,-2,,,true)>>",
            'item="CalendarOne*CalendarTwo",month_offset=-2,anniversary=true',
        ),
    ],
)
def test_macro_conversion(legacy_macro, expected_args):
    converter = ConverterFormat19()
    dom = converter(legacy_macro, import19.CONTENTTYPE_MOINWIKI)
    migrate_macros(dom)  # in-place conversion

    body = list(dom)[0]
    part = list(body)[0]

    assert part.get(moin_page.content_type) == "x-moin/macro;name=MonthCalendar"
    assert part.get(moin_page.alt) == f"<<MonthCalendar({expected_args})>>"

    if len(list(part)) > 0:
        arguments = list(part)[0]
        assert list(arguments)[0] == expected_args
