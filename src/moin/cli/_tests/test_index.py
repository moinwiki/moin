# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.index tests
"""

from pathlib import Path

from moin.cli._tests import run, read_index_dump_latest_revs, assert_p_succcess


def test_index_create(index_create):
    assert_p_succcess(index_create)
    for p in [
        "wiki",
        "wiki/data",
        "wiki/data/default",
        "wiki/data/default/meta",
        "wiki/data/default/data",
        "wiki/data/users",
        "wiki/data/users/meta",
        "wiki/data/users/data",
        "wiki/data/userprofiles",
        "wiki/data/userprofiles/meta",
        "wiki/data/userprofiles/data",
        "wiki/data/help-common",
        "wiki/data/help-common/meta",
        "wiki/data/help-common/data",
        "wiki/data/help-en",
        "wiki/data/help-en/meta",
        "wiki/data/help-en/data",
        "wiki/index",
        "wiki/index/_latest_revs_0.toc",
        "wiki/index/_all_revs_0.toc",
    ]:
        assert Path(p).exists()


def test_index_dump(load_help):
    index_dump = run(["moin", "index-dump", "--no-truncate"])
    assert_p_succcess(index_dump)
    items = read_index_dump_latest_revs(index_dump.stdout.decode())
    cats = [i for i in items if "cat.jpg" in i["name"]]
    assert len(cats) == 1
    cat = cats[0]
    assert "contenttype" in cat
    assert cat["contenttype"] == "image/jpeg"
    assert "namespace" in cat
    assert cat["namespace"] == "help-common"
    assert "rev_number" in cat
    assert cat["rev_number"] == 1
