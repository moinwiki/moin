# -*- coding: utf-8 -*-
# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.md5crypt Tests
"""


import pytest
from MoinMoin.util import md5crypt

def test_unix_md5_crypt():
    # when magic != None
    result = md5crypt.unix_md5_crypt('test_pass', 'Moin_test', '$test_magic$')
    expected = '$test_magic$Moin_tes$JRfmeHgnmCVhVYW.bTtiY1'
    assert result == expected

    # when magic == None
    result = md5crypt.unix_md5_crypt('test_pass', 'Moin_test', None)
    expected = '$1$Moin_tes$hArc67BzmDWtyWWKO5uxQ1'
    assert result == expected

def test_apache_md5_crypt():
    # Here magic == '$apr1$'
    result = md5crypt.apache_md5_crypt('test_pass', 'Moin_test')
    expected = '$apr1$Moin_tes$4/5zV8nADrNv3BJcY1rZX1'
    assert result == expected

