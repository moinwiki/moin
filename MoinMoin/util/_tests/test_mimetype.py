# -*- coding: utf-8 -*-
# Copyright: 2011 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.mimetype Tests
"""

import pytest
from MoinMoin.util import mimetype

class TestMimeType(object):
    """ Test: util.mimetype """
    
    def test_parse_format(self):
        MimeType_obj = mimetype.MimeType(filename = 'test_file.jpg')
        # format in config.parser_text_mimetype
        test = [
        #test_format    # test_mimetype
        ('html',        ('text', 'html')),
        ('css',         ('text', 'css')),
        ('python',      ('text', 'python')),
        ('latex',       ('text', 'latex'))
        ]

        for test_format, test_mimetype in test: 
            result = MimeType_obj.parse_format(test_format)
            assert result == test_mimetype

        # format not in config.parser_text_mimetype
        test = [
        # test_format   # test_mimetype
        ('wiki',        ('text', 'x.moin.wiki')),
        ('irc',         ('text', 'irssi')),
        ('test_random', ('text', 'x-test_random'))
        ]
        
        for test_format, test_mimetype in test:
            result = MimeType_obj.parse_format(test_format)
            assert result == test_mimetype
        result = MimeType_obj.parse_format(test_format)
        
