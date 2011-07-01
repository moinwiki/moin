# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Navibar Tests
"""


from flask import current_app as app

from MoinMoin._tests import wikiconfig
from MoinMoin.themes import ThemeSupport

class TestNaviBar(object):
    class Config(wikiconfig.Config):
        interwiki_map = dict(MoinMoin='http://moinmo.in/', )

    def setup_method(self, method):
        self.theme = ThemeSupport(app.cfg)

    def test_split_navilink(self):
        tests = [
            #(navilink, (href, text, interwiki)),
            ('ItemName', ('/ItemName', 'ItemName', '')),
            ('[[ItemName|LinkText]]', ('/ItemName', 'LinkText', '')),
            ('MoinMoin:ItemName', ('http://moinmo.in/ItemName', 'ItemName', 'MoinMoin')),
            ('[[MoinMoin:ItemName|LinkText]]', ('http://moinmo.in/ItemName', 'LinkText', 'MoinMoin')),
            ('[[wiki:MoinMoin:ItemName|LinkText]]', ('http://moinmo.in/ItemName', 'LinkText', 'MoinMoin')),
            ('http://example.org/', ('http://example.org/', 'http://example.org/', '')),
            ('[[http://example.org/|LinkText]]', ('http://example.org/', 'LinkText', '')),
        ]
        for navilink, expected in tests:
            result = self.theme.split_navilink(navilink)
            assert result == expected

    def test_location_breadcrumbs(self):
        test_result = ThemeSupport.location_breadcrumbs(self.theme, 'test_item')
        test_segment_name, test_item_name, test_item_exists = test_result[0]
        assert test_segment_name == 'test_item'
        assert test_item_name == 'test_item'

