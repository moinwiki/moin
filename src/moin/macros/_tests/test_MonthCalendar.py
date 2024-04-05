# Copyright: 2022 MoinMoin
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.macros.MonthCalendar Tests
"""

from emeraldtree.tree import Element
import pytest

from moin.macros.MonthCalendar import Macro, parseargs, yearmonthplusoffset


def test_parseargs_one():
    """
    checking the handling of explicit and default parameters in parseargs
    """
    args = parseargs(
        'item="TEST-CALENDAR",month_offset=-1,fixed_height=true',  # macro arguments
        "TEST-CALENDAR",
        1990,
        4,
        0,
        False,
        False,
    )  # default values
    assert args == (["TEST-CALENDAR"], 1990, 4, -1, True, False)


def test_parseargs_two():
    args = parseargs(
        'item="WikiWorkingGroup*WikiMacrosSpecialInterestGroup",'
        "year=2020,month=3,month_offset=-4,fixed_height=true,anniversary=false",
        "DefaultPageName",
        1990,
        4,
        -1,
        False,
        True,
    )
    assert args == (["WikiWorkingGroup", "WikiMacrosSpecialInterestGroup"], 2020, 3, -4, True, False)


def test_Macro():
    """
    call MonthCalendar macro and test some attributes of resulting table
    """
    macro_obj = Macro()
    arguments = Element("arguments")
    arguments.append('item="TEST-CALENDAR",month_offset=-1,fixed_height=true')
    result = macro_obj.macro("content", arguments, "page_url", "alternative")

    # the result should be a table with calendar class attribute
    assert result.tag.name == "table"
    assert "calendar" in result.attrib.values()

    result_tags = list(result)
    # the table should have a caption, header and body
    assert result_tags[0].tag.name == "caption"
    assert result_tags[1].tag.name == "table-header"
    assert result_tags[2].tag.name == "table-body"

    # the last macro parameter forces six rows in the calendar output
    # even though some month will only need five week rows
    assert len(result_tags[2]) == 6  # number table rows


@pytest.mark.parametrize(
    "year, month, month_offset, expected_year, expected_month",
    [
        (2000, 1, 3, 2000, 4),
        (1999, 11, 2, 2000, 1),
        (2004, 3, 14, 2005, 5),
        (2006, 2, -4, 2005, 10),
        (2003, 2, -17, 2001, 9),
    ],
)
def test_yearmonthplusoffset(year, month, month_offset, expected_year, expected_month):
    assert yearmonthplusoffset(year, month, month_offset) == (expected_year, expected_month)
