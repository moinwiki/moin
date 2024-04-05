# Copyright: 2012 MoinMoin:PavelSviderski
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.forms Tests
"""

import datetime
import json
from calendar import timegm

from flask import current_app as app

from moin.forms import DateTimeUNIX, JSON, Names
from moin.utils.interwiki import CompositeName
from moin.items import Item
from moin._tests import become_trusted
from moin.constants.keys import ITEMID, NAME, CONTENTTYPE, NAMESPACE


def test_datetimeunix():
    dt = datetime.datetime(2012, 12, 21, 23, 45, 59)
    timestamp = timegm(dt.timetuple())
    dt_u = "2012-12-21 23:45:59"

    d = DateTimeUNIX(timestamp)
    assert d.value == timestamp
    assert d.u == dt_u

    incorrect_timestamp = 99999999999999999
    d = DateTimeUNIX(incorrect_timestamp)
    assert d.value is None
    assert d.u == str(incorrect_timestamp)

    d = DateTimeUNIX(dt)
    assert d.value == timestamp
    assert d.u == dt_u

    # parse time string
    d = DateTimeUNIX(dt_u)
    assert d.value == timestamp
    assert d.u == dt_u

    incorrect_timestring = "2012-10-30"
    d = DateTimeUNIX(incorrect_timestring)
    assert d.value is None
    assert d.u == incorrect_timestring

    d = DateTimeUNIX(None)
    assert d.value is None
    assert d.u == ""


def test_validjson():
    """
    Tests for changes to metadata when modifying an item.

    Does not apply to usersettings form.
    """
    app.cfg.namespace_mapping = [("", "default_backend"), ("ns1", "default_backend"), ("users", "other_backend")]
    item = Item.create("users/existingname")
    meta = {NAMESPACE: "users", CONTENTTYPE: "text/plain;charset=utf-8"}
    become_trusted()
    item._save(meta, data="This is a valid Item.")

    valid_itemid = "a1924e3d0a34497eab18563299d32178"
    # ('names', 'namespace', 'field', 'value', 'result')
    tests = [
        (["somename", "@revid"], "", "", "somename", False),  # item names cannot begin with @
        # TODO for above? - create item @x, get error message, change name in meta to xx,
        # get an item with names @40x and alias of xx
        (["bar", "ns1"], "", "", "bar", False),  # item names cannot match namespace names
        (["foo", "foo", "bar"], "", "", "foo", False),  # names in the name list must be unique.
        # Item names must not match with existing namespaces; items cannot be in 2 namespaces
        (["ns1ns2ns3", "ns1/subitem"], "", "", "valid", False),
        # attempts to change itemid in meta result in "Item(s) named foobar, validname already exist."
        (["foobar", "validname"], "", ITEMID, valid_itemid + "8080", False),
        (["barfoo", "validname"], "", ITEMID, valid_itemid.replace("a", "y"), False),  # similar to above
        # deleting all names from the metadata of an existing item will make it nameless, succeeds
        ([], "", "itemid", valid_itemid, True),
        (["existingname"], "users", "", "existingname", False),  # item already exists
    ]
    for name, namespace, field, value, result in tests:
        meta = {NAME: name, NAMESPACE: namespace}
        x = JSON(json.dumps(meta))
        y = Names(name)
        state = dict(fqname=CompositeName(namespace, field, value), itemid=None, meta=meta)
        value = x.validate(state) and y.validate(state)
        assert value == result
