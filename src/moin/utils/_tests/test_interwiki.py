# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils.interwiki Tests
"""

import tempfile
import os.path
import shutil
import re

import pytest
from flask import current_app as app

from moin.utils.interwiki import split_interwiki, join_wiki, InterWikiMap, url_for_item, _split_namespace, split_fqname
from moin._tests import wikiconfig
from moin.constants.keys import CURRENT
from moin.app import before_wiki


class TestInterWiki:
    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            interwiki_map = {
                "Self": "http://localhost:8080/",
                "MoinMoin": "http://moinmo.in/",
                "OtherWiki": "http://otherwiki.com/",
                "OtherWiki/ns1": "http://otherwiki.com/ns1/",
                "OtherWiki/ns1/ns2": "http://otherwiki.com/ns1/ns2/",
            }

        return Config

    def test_url_for_item(self):
        before_wiki()
        revid = "cdc431e0fc624d6fb8372152dcb66457"

        tests = [
            (("SomePage", "", "", "", CURRENT, "frontend.show_item", False), "/SomePage"),
            # Method signature to understand the tuple parameters
            # (item_name, wiki_name='', namespace='', rev=CURRENT, endpoint='frontend.show_item', _external=False):
            (("SomePage", "", "", "", CURRENT, "frontend.show_item", True), "http://localhost:8080/SomePage"),
            (("SomePage", "", "", "", CURRENT, "frontend.modify_item", False), "/+modify/SomePage"),
            # FIXME if you set interwiki_map = dict(Self='http://localhost:8080', MoinMoin='http://moinmo.in/', ),
            # the above line make it fails, it returns http://localhost/+modify/SomePage
            # (('SomePage', '', '', CURRENT, 'frontend.modify_item', True), 'http://localhost:8080/+modify/SomePage'),
            (("SomeRevID", "", "revid", "", revid, "frontend.show_item", False), f"/+show/+{revid}/@revid/SomeRevID"),
            (("SomePage", "", "", "", revid, "frontend.show_item_meta", False), f"/+meta/+{revid}/SomePage"),
            # Valid namespaces
            (("SomePage", "", "", "ns1", CURRENT, "frontend.show_item", False), "/ns1/SomePage"),
            (("SomeTag", "", "tags", "ns1", CURRENT, "frontend.show_item", False), "/ns1/@tags/SomeTag"),
            (
                ("SomePage", "", "", "ns1/ns2", CURRENT, "frontend.show_item", True),
                "http://localhost:8080/ns1/ns2/SomePage",
            ),
            (("SomePage", "", "", "ns1", CURRENT, "frontend.modify_item", False), "/+modify/ns1/SomePage"),
            (
                ("SomePage", "", "", "ns1/ns2", CURRENT, "frontend.show_item_meta", True),
                "http://localhost:8080/+meta/ns1/ns2/SomePage",
            ),
            (("SomePage", "", "", "ns1", revid, "frontend.show_item", False), f"/+show/+{revid}/ns1/SomePage"),
            (
                ("SomePage", "", "", "ns1/ns2", revid, "frontend.show_item_meta", False),
                f"/+meta/+{revid}/ns1/ns2/SomePage",
            ),
            (
                ("SomeRevID", "", "revid", "ns1/ns2", CURRENT, "frontend.show_item_meta", False),
                "/+meta/ns1/ns2/@revid/SomeRevID",
            ),
            (
                ("SomePage", "MoinMoin", "", "ns1", CURRENT, "frontend.show_item", False),
                "http://moinmo.in/ns1/SomePage",
            ),
            (("SomePage", "MoinMoin", "", "", CURRENT, "frontend.show_item", False), "http://moinmo.in/SomePage"),
            # FIXME will exist a map for this case? maybe there should be a placeholder for it.
            # we need that for wiki farms with common search index and search in non-current revisions.
            (
                ("SomePage", "MoinMoin", "", "", revid, "frontend.show_item", False),
                f"http://moinmo.in/+show/+{revid}/SomePage",
            ),
            (
                ("SomeItemID", "non-existent", "itemid", "", CURRENT, "frontend.show_item", False),
                "/non-existent/@itemid/SomeItemID",
            ),
            (
                ("SomePage", "non-existent", "", "ns1", CURRENT, "frontend.show_item", False),
                "/non-existent/ns1/SomePage",
            ),
        ]

        for (item_name, wiki_name, field, namespace, rev, endpoint, _external), url in tests:
            # Workaround: substitute %40 with @ to allow both Werkzeug versions 2.2. and 2.3 TODO: remove later
            assert (
                re.sub("%40", "@", url_for_item(item_name, wiki_name, field, namespace, rev, endpoint, _external))
                == url
            )

    def test__split_namespace(self):
        map = set()
        map.add("ns1")
        map.add("ns1/ns2")
        tests = [
            ("", ("", "")),
            ("OtherWiki/", ("", "OtherWiki/")),
            ("ns1/", ("ns1", "")),
            ("ns3/foo", ("", "ns3/foo")),
            ("ns1/OtherPage", ("ns1", "OtherPage")),
            ("ns1/ns2/OtherPage", ("ns1/ns2", "OtherPage")),
            ("ns1/ns2/ns1/ns2/OtherPage", ("ns1/ns2", "ns1/ns2/OtherPage")),
            ("SomePage", ("", "SomePage")),
            ("OtherWiki/ns1/OtherPage", ("", "OtherWiki/ns1/OtherPage")),
        ]
        for markup, (namespace, pagename) in tests:
            assert _split_namespace(map, markup) == (namespace, pagename)
            namespace, pagename = _split_namespace(map, markup)

    def test_split_interwiki(self):
        app.cfg.namespace_mapping = [
            ("", "default_backend"),
            ("ns1/", "default_backend"),
            ("ns1/ns2/", "other_backend"),
        ]
        tests = [
            ("", ("Self", "", "name_exact", "")),
            ("OtherWiki/", ("OtherWiki", "", "name_exact", "")),
            ("/ns1/", ("Self", "ns1", "name_exact", "")),
            ("/@itemid/", ("Self", "", "itemid", "")),
            ("/ns3/foo", ("Self", "", "name_exact", "ns3/foo")),
            ("@tags/SomeTag", ("Self", "", "tags", "SomeTag")),
            ("OtherWiki/OtherPage", ("OtherWiki", "", "name_exact", "OtherPage")),
            ("NonExistentWiki/OtherPage", ("Self", "", "name_exact", "NonExistentWiki/OtherPage")),
            ("OtherWiki/ns1/@invalidID/Page", ("OtherWiki", "ns1", "name_exact", "@invalidID/Page")),
            ("/ns1/OtherPage", ("Self", "ns1", "name_exact", "OtherPage")),
            ("/ns1/ns2/OtherPage", ("Self", "ns1/ns2", "name_exact", "OtherPage")),
            ("ns1/OtherPage", ("Self", "ns1", "name_exact", "OtherPage")),
            ("ns1/ns2/OtherPage", ("Self", "ns1/ns2", "name_exact", "OtherPage")),
            ("OtherWiki/ns1/OtherPage", ("OtherWiki", "ns1", "name_exact", "OtherPage")),
            ("OtherWiki/ns1/ns2/OtherPage", ("OtherWiki", "ns1/ns2", "name_exact", "OtherPage")),
            ("OtherWiki/ns1/ns2/@userid/SomeUserID", ("OtherWiki", "ns1/ns2", "userid", "SomeUserID")),
            (
                "OtherWiki/ns3/ns2/@Notfield/OtherPage/foo",
                ("OtherWiki", "", "name_exact", "ns3/ns2/@Notfield/OtherPage/foo"),
            ),
        ]
        for markup, (wikiname, namespace, field, pagename) in tests:
            assert split_interwiki(markup) == (wikiname, namespace, field, pagename)
            wikiname, namespace, field, pagename = split_interwiki(markup)
            assert isinstance(namespace, str)
            assert isinstance(pagename, str)
            assert isinstance(field, str)
            assert isinstance(wikiname, str)

    def testJoinWiki(self):
        tests = [
            (("http://example.org/", "SomePage", "", ""), "http://example.org/SomePage"),
            (("", "SomePage", "", ""), "SomePage"),
            (
                ("http://example.org/?page=$PAGE&action=show", "SomePage", "", ""),
                "http://example.org/?page=SomePage&action=show",
            ),
            (("http://example.org/", "Aktuelle\xc4nderungen", "", ""), "http://example.org/Aktuelle%C3%84nderungen"),
            (
                ("http://example.org/$PAGE/show", "Aktuelle\xc4nderungen", "", ""),
                "http://example.org/Aktuelle%C3%84nderungen/show",
            ),
            (("http://example.org/", "SomeItemID", "itemid", "ns1"), "http://example.org/ns1/@itemid/SomeItemID"),
            (
                ("http://example.org/?page=$PAGE&action=show&namespace=$NAMESPACE", "SomePage", "", "ns1"),
                "http://example.org/?page=SomePage&action=show&namespace=ns1",
            ),
            (
                ("http://example.org/", "Aktuelle\xc4nderungen", "", "ns1\xc4"),
                "http://example.org/ns1%C3%84/Aktuelle%C3%84nderungen",
            ),
            (
                ("http://example.org/$NAMESPACE/$PAGE/show", "Aktuelle\xc4nderungen", "", "ns\xc41"),
                "http://example.org/ns%C3%841/Aktuelle%C3%84nderungen/show",
            ),
            (
                ("http://example.org/@$FIELD/$PAGE/show", "Aktuelle\xc4nderungen", "itemid", ""),
                "http://example.org/@itemid/Aktuelle%C3%84nderungen/show",
            ),
        ]
        for (baseurl, pagename, field, namespace), url in tests:
            assert join_wiki(baseurl, pagename, field, namespace) == url

    def test_split_fqname(self):
        app.cfg.namespace_mapping = [
            ("", "default_backend"),
            ("ns1/", "default_backend"),
            ("ns1/ns2/", "other_backend"),
        ]
        tests = [
            ("ns1/ns2/@itemid/SomeItemID", ("ns1/ns2", "itemid", "SomeItemID")),
            ("ns3/@itemid/SomeItemID", ("", "name_exact", "ns3/@itemid/SomeItemID")),
            ("Page", ("", "name_exact", "Page")),
            ("ns1/ns2/@tags/SomeTag", ("ns1/ns2", "tags", "SomeTag")),
            ("@tags/SomeTag", ("", "tags", "SomeTag")),
            ("ns1/ns2/@notid", ("ns1/ns2", "name_exact", "@notid")),
            ("ns1/ns2/ns3/Thisisapagename/ns4", ("ns1/ns2", "name_exact", "ns3/Thisisapagename/ns4")),
        ]
        for url, (namespace, field, pagename) in tests:
            assert split_fqname(url) == (namespace, field, pagename)


class TestInterWikiMapBackend:
    """
    tests for interwiki map
    """

    def test_load_file(self):
        """
        Test that InterWikiMap.from_file correctly loads file objects.
        """
        tmpdir = tempfile.mkdtemp()

        # test an invalid file
        with pytest.raises(IOError):
            InterWikiMap.from_file(os.path.join(tmpdir, "void"))

        # test a consistent valid file
        testfile = os.path.join(tmpdir, "foo.iwm")
        with open(testfile, "w") as f:
            f.write("foo bar\n" "baz spam\n" "ham end end # this is really the end.")
        testiwm = InterWikiMap.from_file(testfile)
        assert testiwm.iwmap == dict(foo="bar", baz="spam", ham="end end")

        # test a malformed file
        testfile = os.path.join(tmpdir, "bar.iwm")
        with open(testfile, "w") as f:
            f.write("# This is a malformed interwiki file\n" "fails # ever")
        with pytest.raises(ValueError):
            InterWikiMap.from_file(testfile)

        # finally destroy everything
        shutil.rmtree(tmpdir)

    def test_load_string(self):
        """
        Test that InterWikiMap.from_unicode correctly loads unicode objects.
        """
        # test for void wiki maps
        assert InterWikiMap.from_string("").iwmap == dict()
        assert InterWikiMap.from_string("#spam\r\n").iwmap == dict()
        # test for comments
        s = (
            "# foo bar\n"
            "#spamham\r\n"
            "#       space     space\n"
            "foo bar\r\n"
            "ham spam # this is a valid description"
        )
        assert InterWikiMap.from_string(s).iwmap == dict(foo="bar", ham="spam")
        # test for valid strings
        s = "link1 http://link1.com/\r\n" "link2 http://link2.in/\r\n"
        assert InterWikiMap.from_string(s).iwmap == dict(link1="http://link1.com/", link2="http://link2.in/")
        # test invalid strings
        with pytest.raises(ValueError):
            InterWikiMap.from_string("foobarbaz")

    def test_real_interwiki_map(self):
        """
        Test a 'real' interwiki file.
        """
        this_dir = os.path.dirname(__file__)
        testfile = os.path.join(this_dir, "test_interwiki_intermap.txt")
        testiwm = InterWikiMap.from_file(testfile)

        assert "MoinMaster" in testiwm.iwmap
        assert testiwm.iwmap["MoinMaster"] == "https://master.moinmo.in/"
        assert "PythonInfo" in testiwm.iwmap
        assert "this" not in testiwm.iwmap
        assert testiwm.iwmap["MoinMoin"] == "https://moinmo.in/"
        assert testiwm.iwmap["hg"] == "https://www.mercurial-scm.org/wiki/"
        assert testiwm.iwmap["h2g2"] == "http://h2g2.com/dna/h2g2/"


coverage_modules = ["moin.utils.interwiki"]
