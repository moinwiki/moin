# Copyright: 2023 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - Migration of MonthCalendar macro (moin1.9) to its new syntax (moin2)

The MonthCalendar macro used to have comma-separated non-name-value arguments
such as <<MonthCalendar('TestCalendar',,,-1,,1)>>, now it has named parameters
such as <<MonthCalendar(item='TestCalendar', offset=-1, fixed_height=true)>>
"""
from moin.cli.migration.moin19 import macro_migration
from moin.utils import paramparser
from moin.utils.tree import moin_page

from moin import log

logging = log.getLogger(__name__)


CONTENT_TYPE_MACRO_FORMATTER = "x-moin/macro;name={}"
MACRO_NAME_MONTH_CALENDAR = "MonthCalendar"


def parseargs_legacy(
    args, defpagename, defyear, defmonth, defoffset, defoffset2, defheight6, defanniversary, deftemplate
):
    """Slightly modified parsing function from MonthCalendar.py in moin-1.9

    From the moin-1.9 version of the function
    * the request argument was dropped
    * get_unicode was changed to get_str
    """
    args = paramparser.parse_quoted_separated(args, name_value=False)
    args += [None] * 8  # fill up with None to trigger defaults
    parmpagename, parmyear, parmmonth, parmoffset, parmoffset2, parmheight6, parmanniversary, parmtemplate = args[:8]
    parmpagename = paramparser.get_str(parmpagename, "pagename", defpagename)
    parmyear = paramparser.get_int(parmyear, "year", defyear)
    parmmonth = paramparser.get_int(parmmonth, "month", defmonth)
    parmoffset = paramparser.get_int(parmoffset, "offset", defoffset)
    parmoffset2 = paramparser.get_int(parmoffset2, "offset2", defoffset2)
    parmheight6 = paramparser.get_bool(parmheight6, "height6", defheight6)
    parmanniversary = paramparser.get_bool(parmanniversary, "anniversary", defanniversary)
    parmtemplate = paramparser.get_str(parmtemplate, "template", deftemplate)

    return parmpagename, parmyear, parmmonth, parmoffset, parmoffset2, parmheight6, parmanniversary, parmtemplate


def convert_month_calendar_macro_syntax(node):
    """Convert the given MonthCalendar macro node to the new syntax in-place

    MonthCalendar used to have unnamed parameters in moin-1.9. The syntax
    has been changed to name-value parameters in moin2. Migrate the given
    macro accordingly.

    Example conversions:

    | moin1.9                          | moin2                                |
    |----------------------------------|--------------------------------------|
    | <<MonthCalendar()>>              | <<MonthCalendar()>>                  |
    | <<MonthCalendar('TestPage')>>    | <<MonthCalendar(item="TestPage")>>   |
    | <<MonthCalendar('TestPage',      | <<MonthCalendar(item="TestPage",     |
    |                 1995,3,2,,1,,)>> |                 year=1995, month=3,  |
    |                                  |                 month_offset=2,      |
    |                                  |                 fixed_height=true)>> |

    :param node: the DOM node matching the MonthCalendar macro content type
    :type node: emeraldtree.tree.Element
    """

    # content type
    new_content_type = CONTENT_TYPE_MACRO_FORMATTER.format("MonthCalendar")
    node.set(moin_page.content_type, new_content_type)

    # arguments
    args_before = None
    args_after = ""
    for elem in node.iter_elements():
        if elem.tag.name == "arguments":
            args_before = elem.text
    if args_before:
        (parmpagename, parmyear, parmmonth, parmoffset, parmoffset2, parmheight6, parmanniversary, parmtemplate) = (
            parseargs_legacy(args_before, None, None, None, None, None, False, False, None)
        )

        # Warn if parmoffset2 or parmtemplate are set,
        # they are not supported by the current
        # MonthCalendar version, so they cannot be migrated
        if parmoffset2:
            # TODO: add more details to the log
            logging.warning("MonthCalendar macro parameter 'offset2' cannot be migrated")
        if parmtemplate:
            logging.warning("MonthCalendar macro parameter 'template' cannot be migrated")

        args_after_dict = {
            "item": f'"{parmpagename}"' if parmpagename else None,
            "year": parmyear,
            "month": parmmonth,
            "month_offset": parmoffset,
            "fixed_height": "true" if parmheight6 else False,
            "anniversary": "true" if parmanniversary else False,
        }

        args_after = ",".join([f"{key}={args_after_dict[key]}" for key in args_after_dict if args_after_dict[key]])

    for elem in node.iter_elements():
        if elem.tag.name == "arguments":
            elem.clear()
            elem.append(args_after)

    # 'alt' attribute
    new_alt = f"<<MonthCalendar({args_after})>>"
    node.set(moin_page.alt, new_alt)


macro_migration.register_macro_migration(
    CONTENT_TYPE_MACRO_FORMATTER.format(MACRO_NAME_MONTH_CALENDAR), convert_month_calendar_macro_syntax
)
