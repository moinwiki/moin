# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.set_meta tests
"""

from moin._tests import get_dirs
from moin.constants.keys import NAME, REVID, REV_NUMBER, PARENTID, DATAID, ITEMID
from moin.cli._tests import run, assert_p_succcess, read_index_dump


def test_set_meta(index_create2):
    moin_dir, _ = get_dirs("")
    data_dir = moin_dir / "src" / "moin" / "cli" / "_tests" / "data"
    put = run(["moin", "item-put", "-m", data_dir / "Home.meta", "-d", data_dir / "Home.data", "-o"])
    assert_p_succcess(put)
    set_meta = run(["moin", "maint-set-meta", "-q", "Home", "-k", NAME, "-v", '["Home", "AnotherName"]'])
    assert_p_succcess(set_meta)
    index_dump = run(["moin", "index-dump", "--no-truncate"])
    assert_p_succcess(index_dump)
    items = {item[REV_NUMBER]: item for item in read_index_dump(index_dump.stdout.decode())}
    assert {1, 2} == set(items.keys())
    orig_item = items[1]
    assert ["Home"] == orig_item[NAME]
    new_item = items[2]
    assert ["Home", "AnotherName"] == new_item[NAME]
    assert orig_item[REVID] == new_item[PARENTID]
    assert orig_item[ITEMID] == new_item[ITEMID]
    assert orig_item[DATAID] == new_item[DATAID]
