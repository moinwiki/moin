# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.cli.maint.set_meta.
"""

import pytest

from click.testing import CliRunner
from moin._tests import get_dirs
from moin.constants.keys import NAME, REVID, REV_NUMBER, PARENTID, DATAID, ITEMID
from moin.cli import cli
from moin.cli._tests import read_index_dump


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.usefixtures("index_create2")
def test_set_meta(runner: CliRunner) -> None:
    moin_dir, _ = get_dirs("")
    data_dir = moin_dir / "cli" / "_tests" / "data"
    put = runner.invoke(cli, ["item-put", "-m", data_dir / "Home.meta", "-d", data_dir / "Home.data", "-o"])
    assert put.exit_code == 0
    set_meta = runner.invoke(cli, ["maint-set-meta", "-q", "Home", "-k", NAME, "-v", '["Home", "AnotherName"]'])
    assert set_meta.exit_code == 0
    index_dump = runner.invoke(cli, ["index-dump", "--no-truncate"])
    assert index_dump.exit_code == 0
    items = {item[REV_NUMBER]: item for item in read_index_dump(index_dump.stdout)}
    assert {1, 2} == set(items.keys())
    orig_item = items[1]
    assert ["Home"] == orig_item[NAME]
    new_item = items[2]
    assert ["Home", "AnotherName"] == new_item[NAME]
    assert orig_item[REVID] == new_item[PARENTID]
    assert orig_item[ITEMID] == new_item[ITEMID]
    assert orig_item[DATAID] == new_item[DATAID]
