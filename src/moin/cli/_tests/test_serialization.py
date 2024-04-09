# Copyright: 2023 MoinMoin project
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.serialization tests
"""

import json
import os
from pathlib import Path

from moin._tests import get_dirs
from moin.cli._tests import run, assert_p_succcess, read_index_dump_latest_revs, getBackupPath
from moin.constants.keys import NAME, MTIME, CONTENT, BACKENDNAME, NAMESPACE
from moin import log

logging = log.getLogger(__name__)


def test_save_all(artifact_dir, save_all):
    assert_p_succcess(save_all)
    assert getBackupPath("backup.moin").exists()


def load(restore_dir, backup_name, artifact_dir, args=None):
    restore_dir.mkdir()
    os.chdir(restore_dir)
    try:
        for command in (
            ["moin", "create-instance"],
            ["moin", "index-create"],
            ["moin", "load", "-f", getBackupPath(backup_name)] + (args if args else []),
        ):
            p = run(command)
            assert_p_succcess(p)
    finally:
        os.chdir(artifact_dir)  # insure we return to archive_dir for other tests


def test_load_all(artifact_dir, save_all):
    restore_dir = Path(artifact_dir / "restore_all")
    load(restore_dir, "backup.moin", artifact_dir)


def test_save_default_ns(artifact_dir, save_default):
    assert_p_succcess(save_default)
    assert getBackupPath("backup_default.moin").exists()


def test_load_default_ns(artifact_dir, save_default):
    moin_dir, _ = get_dirs("")
    welcome_dir = moin_dir / "src" / "moin" / "help" / "welcome"
    expected_metas = {}
    for data_fn in welcome_dir.glob("*.meta"):
        with open(data_fn) as f:
            meta = json.load(f)
            if meta[NAMESPACE] != "":
                continue
            name = meta[NAME][0]
            expected_metas[name] = meta
    restore_dir = Path(artifact_dir / "restore_default")
    load(restore_dir, "backup_default.moin", artifact_dir)
    os.chdir(restore_dir)
    try:
        index_dump = run(["moin", "index-dump", "--no-truncate"])
        metas = {}
        contents = {}
        items = read_index_dump_latest_revs(index_dump.stdout.decode())
        for item in items:
            name = item[NAME][0]
            content = item.pop(CONTENT)
            metas[name] = item
        assert set(expected_metas.keys()) == set(metas.keys())
        for name, meta in metas.items():
            expected_meta = expected_metas[name]
            for k, v in meta.items():
                if k in expected_meta:
                    if k == MTIME:
                        continue  # load replaces all mtimes
                    expected_v = expected_meta[k]
                    assert expected_v == v, f"key {k} {name}.meta = {repr(expected_v)} index-dump = {repr(v)}"
        for name, content in contents.items():
            with open(welcome_dir / f"{name}.data") as f:
                expected_content = f.read()
                assert expected_content, content
    finally:
        os.chdir(artifact_dir)  # insure we return to archive_dir for other tests


def test_load_new_ns(artifact_dir, save_default):
    restore_dir = Path(artifact_dir / "restore_new_ns")
    load(restore_dir, "backup_default.moin", artifact_dir, ["-o", "", "-n", "help-en"])
    os.chdir(restore_dir)
    try:
        index_dump = run(["moin", "index-dump", "--no-truncate"])
        items = list(read_index_dump_latest_revs(index_dump.stdout.decode()))
        assert 1 == len(items)
        item = items[0]
        assert ["Home"] == item[NAME]
        assert "help-en" == item[BACKENDNAME]
    finally:
        os.chdir(artifact_dir)  # insure we return to archive_dir for other tests


def test_load_corrupt(artifact_dir2, index_create2):
    moin_dir, _ = get_dirs("cli")
    data_dir = moin_dir / "src" / "moin" / "cli" / "_tests" / "data"
    # item-put below errors out without the -o, see moin.storage.backends.stores.store
    p = run(["moin", "item-put", "-m", data_dir / "Corrupt.meta", "-d", data_dir / "Corrupt.data", "-o"])
    assert_p_succcess(p)
    backup_name = "backup_corrupt.moin"
    p = run(["moin", "save", "-b", "default", "-f", getBackupPath(backup_name)])
    assert_p_succcess(p)
    restore_dir = Path(artifact_dir2 / "restore_new_ns")
    load(restore_dir, backup_name, artifact_dir2)
