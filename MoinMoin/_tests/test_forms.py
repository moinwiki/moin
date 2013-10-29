# Copyright: 2012 MoinMoin:PavelSviderski
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.forms Tests
"""

import datetime
import json
from calendar import timegm

from flask import current_app as app
from flask import g as flaskg

from MoinMoin.forms import DateTimeUNIX, JSON, Names
from MoinMoin.util.interwiki import CompositeName
from MoinMoin.items import Item
from MoinMoin._tests import become_trusted
from MoinMoin.constants.keys import ITEMID, NAME, CONTENTTYPE, NAMESPACE, FQNAME


def test_datetimeunix():
    dt = datetime.datetime(2012, 12, 21, 23, 45, 59)
    timestamp = timegm(dt.timetuple())
    dt_u = u'2012-12-21 23:45:59'

    d = DateTimeUNIX(timestamp)
    assert d.value == timestamp
    assert d.u == dt_u

    incorrect_timestamp = 999999999999
    d = DateTimeUNIX(incorrect_timestamp)
    assert d.value is None
    assert d.u == unicode(incorrect_timestamp)

    d = DateTimeUNIX(dt)
    assert d.value == timestamp
    assert d.u == dt_u

    # parse time string
    d = DateTimeUNIX(dt_u)
    assert d.value == timestamp
    assert d.u == dt_u

    incorrect_timestring = u'2012-10-30'
    d = DateTimeUNIX(incorrect_timestring)
    assert d.value is None
    assert d.u == incorrect_timestring

    d = DateTimeUNIX(None)
    assert d.value is None
    assert d.u == u''


def test_validjson():
    app.cfg.namespace_mapping = [(u'', 'default_backend'), (u'ns1/', 'default_backend'), (u'ns1/ns2/', 'other_backend')]
    item = Item.create(u'ns1/ns2/existingname')
    meta = {NAMESPACE: u'ns1/ns2', CONTENTTYPE: u'text/plain;charset=utf-8'}
    become_trusted()
    item._save(meta, data='This is a valid Item.')

    valid_itemid = 'a1924e3d0a34497eab18563299d32178'
    # ('names', 'namespace', 'field', 'value', 'result')
    tests = [([u'somename', u'@revid'], '', '', 'somename', False),
             ([u'bar', u'ns1'], '', '', 'bar', False),
             ([u'foo', u'foo', u'bar'], '', '', 'foo', False),
             ([u'ns1ns2ns3', u'ns1/subitem'], '', '', 'valid', False),
             ([u'foobar', u'validname'], '', ITEMID, valid_itemid + '8080', False),
             ([u'barfoo', u'validname'], '', ITEMID, valid_itemid.replace('a', 'y'), False),
             ([], '', 'itemid', valid_itemid, True),
             ([u'existingname'], 'ns1/ns2', '', 'existingname', False),
             ]
    for name, namespace, field, value, result in tests:
        meta = {NAME: name, NAMESPACE: namespace}
        x = JSON(json.dumps(meta))
        y = Names(name)
        state = dict(fqname=CompositeName(namespace, field, value), itemid=None, meta=meta)
        value = x.validate(state) and y.validate(state)
        assert value == result
