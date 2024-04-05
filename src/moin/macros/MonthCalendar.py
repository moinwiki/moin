# Copyright: 2002-2009 MoinMoin:ThomasWaldmann
# Copyright: 2022 MoinMoin:
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MonthCalendar Macro

MonthCalendar - generates a Calendar.

You can use this macro to put a month's calendar page on a Wiki page.

The days are links to Wiki pages following this naming convention:
BasePageName/year-month-day

Parameters:

    <<MonthCalendar(item,year,month,month_offset,fixed_height,anniversary)>>

    each parameter can be empty and then defaults to currentpage or currentdate or monthoffset=0
    item: str, the base page for calendar events,
          every day in the calendar will link to 'BasePage/yyyy-mm-dd'
          (or 'BasePage/mm-dd' respectively, if anniversary is set)
          to show details of the event(s),
          defaults to the current page
    year: int, the year to show a calendar page for,
          defaults to the current year
    month: int, the month to show a calendar page for,
           defaults to the current month
    month_offset: int, an offset in months to apply to the given year and month parameter,
                  can be helpful when aiming to display multiple calendar pages on a page,
                  for example one for the current month and one for the next month
                  (<<MonthCalendar()>> <<MonthCalendar(month_offset=1),
                  can be positive or negative,
                  defaults to 0
    fixed_height: bool, create a calendar with six rows, no matter how many
                  rows are needed for the month display,
                  defaults to false
    anniversary: bool, link days to 'BasePage/mm-dd' instead of 'BasePage/yyyy-mm-dd'
                 to be able to create calendars for yearly events such as anniversaries,
                 birthdays and so on,
                 defaults to false

Notes:

. . .

Examples:
    Calendar of current month for current page:
    <<MonthCalendar>>

    Calendar of last month:
    <<MonthCalendar(month_offset=-1)>>

    Calendar of next month:
    <<MonthCalendar(month_offset=+1)>>

    Calendar of Page SampleUser, this year's december:
    <<MonthCalendar(item="SampleUser",month=12)>>

    Calendar of current Page, this year's december:
    <<MonthCalendar(month=12)>>

    Calendar of December, 2022:
    <<MonthCalendar(year=2022,month=12)>>

    Calendar of the month two months after December, 2022
    (maybe doesn't make much sense, but is possible)
    <<MonthCalendar(year=2022,month=12,month_offset=+2)>>

    Calendar of year 2023 (every month padded to height of 6):
    ||||||Year 2023||
    ||<<MonthCalendar(year=2023,month=1,fixed_height=true)>>||<<MonthCalendar(year=2023,month=2,fixed_height=true)>>||<<MonthCalendar(year=2023,month=3,fixed_height=true)>>||
    ||<<MonthCalendar(year=2023,month=4,fixed_height=true)>>||<<MonthCalendar(year=2023,month=5,fixed_height=true)>>||<<MonthCalendar(year=2023,month=6,fixed_height=true)>>||
    ||<<MonthCalendar(year=2023,month=7,fixed_height=true)>>||<<MonthCalendar(year=2023,month=8,fixed_height=true)>>||<<MonthCalendar(year=2023,month=9,fixed_height=true)>>||
    ||<<MonthCalendar(year=2023,month=10,fixed_height=true)>>||<<MonthCalendar(year=2023,month=11,fixed_height=true)>>||<<MonthCalendar(year=2023,month=12,fixed_height=true)>>||

"""

import calendar
from datetime import datetime
import re

from flask import request

from moin.i18n import _
from moin.macros._base import MacroInlineBase
from moin.utils import paramparser
from moin.utils.iri import Iri
from moin.utils.tree import moin_page
from moin.utils.tree import xlink
from moin.storage.middleware.indexing import search_names

calendar.setfirstweekday(calendar.MONDAY)


def build_dom_calendar_table(rows, head=None, caption=None, cls=None):
    """
    Build a DOM table with data from <rows>.
    """
    table = moin_page.table()
    if cls is not None:
        table.attrib[moin_page("class")] = cls

    if caption is not None:
        table_caption = moin_page.caption()
        table_caption.append(caption)
        table.append(table_caption)

    if head is not None:
        table_head = moin_page.table_header()
        table_row = moin_page.table_row()
        for _idx, cell_tuple in enumerate(head):
            (cell, cell_class) = cell_tuple
            table_cell = moin_page.table_cell(children=[cell])
            table_cell.attrib[moin_page("class")] = cell_class
            table_row.append(table_cell)
        table_head.append(table_row)
        table.append(table_head)
    table_body = moin_page.table_body()

    for row in rows:
        table_row = moin_page.table_row()
        for cell_tuple in row:

            # - cell content
            # - href for <a> tag
            # - CSS class for <td> tag
            (cell, cell_addr, cell_class) = cell_tuple

            # empty cell
            if not cell_addr:
                table_cell = moin_page.table_cell(children=[cell])
                table_cell.attrib[moin_page("class")] = cell_class

            # cell with link to calendar
            else:
                iri = Iri(scheme="wiki", path="/" + cell_addr)
                table_a = moin_page.a(attrib={xlink.href: iri}, children=[cell])
                table_cell = moin_page.table_cell(children=[table_a])
                table_cell.attrib[moin_page("class")] = cell_class
            table_row.append(table_cell)
        table_body.append(table_row)
    table.append(table_body)
    return table


def yearmonthplusoffset(year, month, offset):
    """calculate new year/month from year/month and offset"""
    month += offset
    # handle offset and under/overflows - quick and dirty, yes!
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return year, month


def parseargs(args, defpagename, defyear, defmonth, defoffset, defheight6, defanniversary):
    """parse macro arguments"""
    _, args, _ = paramparser.parse_quoted_separated(args)
    parmpagename = paramparser.get_str(args.get("item"), "item", defpagename)
    parmyear = paramparser.get_int(args.get("year"), "year", defyear)
    parmmonth = paramparser.get_int(args.get("month"), "month", defmonth)
    parmoffset = paramparser.get_int(args.get("month_offset"), "month_offset", defoffset)
    parmheight6 = paramparser.get_bool(args.get("fixed_height"), "fixed_height", defheight6)
    parmanniversary = paramparser.get_bool(args.get("anniversary"), "anniversary", defanniversary)

    # multiple pagenames separated by "*" - split into list of pagenames
    parmpagename = re.split(r"\*", parmpagename)

    return parmpagename, parmyear, parmmonth, parmoffset, parmheight6, parmanniversary


class Macro(MacroInlineBase):
    """return a table with a month calendar"""

    def macro(self, content, arguments, page_url, alternative):

        # find page name of current page
        # to be able to use it as a default page name
        this_page = request.path[1:]

        if this_page.startswith("+modify/"):
            this_page = this_page.split("/", 1)[1]

        # get arguments from the macro if available,
        # arguments will be None for <<MonthCalendar>>
        # and <<MonthCalendar()>>
        args = arguments[0] if arguments else ""

        # get default arguments for year and month
        # and current day for calendar styling
        currentyear = datetime.now().year
        currentmonth = datetime.now().month
        currentday = datetime.now().day

        # parse and check arguments,
        # set default values if necessary
        parmpagename, parmyear, parmmonth, parmoffset, parmheight6, anniversary = parseargs(
            args, this_page, currentyear, currentmonth, 0, False, False
        )

        year, month = yearmonthplusoffset(parmyear, parmmonth, parmoffset)

        # get the calendar
        monthcal = calendar.monthcalendar(year, month)

        # european / US differences
        months = (
            _("January"),
            _("February"),
            _("March"),
            _("April"),
            _("May"),
            _("June"),
            _("July"),
            _("August"),
            _("September"),
            _("October"),
            _("November"),
            _("December"),
        )
        # Set things up for Monday or Sunday as the first day of the week
        if calendar.firstweekday() == calendar.MONDAY:
            wkend = (5, 6)
            wkdays = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))
        if calendar.firstweekday() == calendar.SUNDAY:
            wkend = (0, 6)
            wkdays = (_("Sun"), _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"))

        calcaption = f"{months[month - 1]} {year}"
        calhead = []

        # get list of calendar items for given month
        item_month = f"{parmpagename[0]:s}/{year:4d}-{month:02d}-"
        date_results = search_names(item_month, limit=100)

        r7 = range(7)

        for wkday in r7:
            wday = _(wkdays[wkday])
            if wkday in wkend:
                day_class = "cal-weekend"
            else:
                day_class = "cal-workday"
            calhead.append((wday, day_class))

        # parmheight6 true: show 6 week rows even if month has 5 weeks only
        if parmheight6:
            while len(monthcal) < 6:
                monthcal = monthcal + [[0, 0, 0, 0, 0, 0, 0]]

        calrows = []
        for week in monthcal:
            calweek = []
            for wkday in r7:
                day = week[wkday]
                day_addr = ""
                day_class = "cal-emptyday"
                if not day:
                    # '\xa0' is a non-breaking space (just like &nbsp;
                    # in html) to make sure empty cells have the same
                    # height as rows with content
                    calweek.append(("\xa0", None, "cal-invalidday"))
                else:
                    # we only process the first calendar (or item name)
                    # mentioned in the macro parameters (in case separate
                    # pages are separated by "*")
                    page = parmpagename[0]

                    if anniversary:
                        link = f"{page:s}/{month:02d}-{day:02d}"
                    else:
                        link = f"{page:s}/{year:4d}-{month:02d}-{day:02d}"
                    day_addr = link

                    if day_addr in date_results:
                        day_class = "cal-usedday"

                    if day == currentday and month == currentmonth and year == currentyear:
                        day_class = "cal-today"

                    calweek.append((str(day), day_addr, day_class))
            calrows.append(calweek)

        ret = build_dom_calendar_table(rows=calrows, head=calhead, caption=calcaption, cls="calendar")
        return ret
