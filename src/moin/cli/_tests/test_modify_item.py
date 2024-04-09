# Copyright: 2023-2024 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.modify_item tests
"""

import json
from pathlib import Path
from time import sleep

from moin._tests import get_dirs
from moin.cli._tests import run, assert_p_succcess, read_index_dump_latest_revs, read_index_dump
from moin.constants.keys import REVID, PARENTID, SIZE, REV_NUMBER, NAMES


def validate_meta(expected, actual, message):
    for d in expected, actual:
        del d["address"]  # remove elements which may not match
        del d["mtime"]
        try:
            del d["userid"]
        except KeyError:
            pass
        for k in ["externallinks", "itemtransclusions", "itemlinks"]:
            d[k] = set(d[k])  # ignore ordering for these keys
    assert expected == actual, message


def test_load_help(load_help):
    assert_p_succcess(load_help[0])
    assert_p_succcess(load_help[1])


def test_welcome(welcome):
    assert_p_succcess(welcome)


def test_dump_help(load_help):
    moin_dir, artifact_dir = get_dirs("cli")
    help_dir = Path("my_help")
    source_help_dir = moin_dir / "src" / "moin" / "help"
    with open(source_help_dir / "help-en" / "Home.data", newline="") as f:
        crlf_option = "--crlf" if "\r\n" in f.read() else "--no-crlf"
    for help_subdir in ["help-common", "help-en"]:
        help_subdir_path = help_dir / help_subdir
        if not help_subdir_path.exists():
            help_subdir_path.mkdir(parents=True)
        dump_help = run(["moin", "dump-help", "-n", help_subdir, "-p", help_dir, crlf_option])
        assert_p_succcess(dump_help)
        source_help_subdir = source_help_dir / help_subdir
        expected_data_file_names = {p.name for p in source_help_subdir.glob("*.data")}
        data_file_names = {p.name for p in help_subdir_path.glob("*.data")}
        assert expected_data_file_names == data_file_names
        for data_file_name in expected_data_file_names:
            with open(help_subdir_path / data_file_name, "rb") as f:
                data = f.read()
            with open(source_help_subdir / data_file_name, "rb") as f:
                expected_data = f.read()
            assert expected_data == data, f"{data_file_name} in dump not matching to source"
            meta_file_name = f"{str(data_file_name)[0:-5]}.meta"
            with open(help_subdir_path / meta_file_name) as f:
                meta = json.load(f)
            with open(source_help_subdir / meta_file_name) as f:
                expected_meta = json.load(f)
            validate_meta(
                expected_meta, meta, f"{source_help_subdir / meta_file_name} != {help_subdir_path / meta_file_name}"
            )


def test_item_get(load_help):
    """extract an item from help and validate data and meta match original files in moin/help"""
    item_get = run(["moin", "item-get", "-n", "help-common/cat.jpg", "-m", "cat.meta", "-d", "cat.data"])
    assert_p_succcess(item_get)
    assert Path("cat.data").exists()
    assert Path("cat.meta").exists()
    moin_dir, _ = get_dirs("cli")
    with open("cat.meta") as f:
        meta_cat = json.load(f)
    with open(moin_dir / "src" / "moin" / "help" / "help-common" / "cat.jpg.meta") as f:
        meta_cat_expected = json.load(f)
    validate_meta(
        meta_cat_expected,
        meta_cat,
        f"{moin_dir / 'src' / 'moin' / 'help' / 'help-common' / 'cat.jpg.meta'} != cat.meta",
    )
    with open("cat.data", "rb") as f:
        cat_bytes = f.read()
    with open(moin_dir / "src" / "moin" / "help" / "help-common" / "cat.jpg.data", "rb") as f:
        cat_bytes_expected = f.read()
    assert cat_bytes_expected == cat_bytes


def test_item_put(index_create2):
    """validate ability to add a new item to the wiki via item-put and extract using item-get

    include an item with non-ascii characters in name, tags and summary

    check for ability to handle non-ascii characters in index-dump"""
    for page in ["Home", "help-common/Home", "MyRussianPage"]:
        page_filename = page.replace("/", "-")
        item_get_fail = run(
            ["moin", "item-get", "-n", page, "-m", f"{page_filename}.meta", "-d", f"{page_filename}.data"]
        )
        assert item_get_fail.returncode != 0
        moin_dir, _ = get_dirs("")
        data_dir = moin_dir / "src" / "moin" / "cli" / "_tests" / "data"
        item_put = run(
            ["moin", "item-put", "-m", data_dir / f"{page_filename}.meta", "-d", data_dir / f"{page_filename}.data"]
        )
        assert_p_succcess(item_put)
        item_get = run(["moin", "item-get", "-n", page, "-m", f"{page_filename}.meta", "-d", f"{page_filename}.data"])
        assert_p_succcess(item_get)
    index_dump = run(["moin", "index-dump", "--no-truncate"])
    index_dump_data = read_index_dump_latest_revs(index_dump.stdout.decode())
    my_items = [i for i in index_dump_data if "МояСтраница" in i["name"]]
    assert 1 == len(my_items)
    my_item = my_items[0]
    assert "тест на использование ру́сского алфави́т" == my_item["summary"]
    assert ["русский"] == my_item["tags"]


def test_item_rev(index_create2):
    """test loading multiple versions of same page

    validate -o option when present, revid in meta file is retained otherwise new revid is generated

    validate handling of newline at end of file

    *  MyPage-v1 does not have newline at end in storage (size = 16)
    *  MyPage-v2 has newline at end in storage (size = 18)
    *  in both cases, item-get will write file with \n at end of file"""
    moin_dir, _ = get_dirs("cli2")
    data_dir = moin_dir / "src" / "moin" / "cli" / "_tests" / "data"
    put1 = run(["moin", "item-put", "-m", data_dir / "MyPage-v1.meta", "-d", data_dir / "MyPage-v1.data", "-o"])
    assert_p_succcess(put1)
    sleep(1.1)  # MTIME is stored as int in index file, sleep here to guarntee proper sorting of revs for index_revision
    put2 = run(["moin", "item-put", "-m", data_dir / "MyPage-v2.meta", "-d", data_dir / "MyPage-v2.data", "-o"])
    assert_p_succcess(put2)
    item_get2 = run(["moin", "item-get", "-n", "MyPage", "-m", "MyPage-v2.meta", "-d", "MyPage-v2.data", "--crlf"])
    assert_p_succcess(item_get2)
    with open("MyPage-v2.data", newline="") as f:
        assert f.read() == "MyPage version 2\r\n"
    with open("MyPage-v2.meta") as f:
        v2_meta = json.load(f)
    assert v2_meta["size"] == 18  # newline at end is 2 chars \r\n
    with open(data_dir / "MyPage-v1.meta") as f:
        v1_meta = json.load(f)
    v1_revid = v1_meta["revid"]
    assert v1_meta["size"] == 16
    item_get1 = run(
        ["moin", "item-get", "-n", "MyPage", "-m", "MyPage-v1.meta", "-d", "MyPage-v1.data", "-r", v1_revid, "--crlf"]
    )
    assert_p_succcess(item_get1)
    with open("MyPage-v1.data", newline="") as f:
        assert f.read() == "MyPage version 1\r\n"
    put3 = run(["moin", "item-put", "-m", "MyPage-v1.meta", "-d", "MyPage-v1.data"])
    assert_p_succcess(put3)
    item_get1_1 = run(
        ["moin", "item-get", "-n", "MyPage", "-m", "MyPage-v1_1.meta", "-d", "MyPage-v1_1.data", "--crlf"]
    )
    assert_p_succcess(item_get1_1)
    with open("MyPage-v1_1.data", newline="") as f:
        assert f.read() == "MyPage version 1\r\n"
    with open("MyPage-v1_1.meta") as f:
        v1_1_meta = json.load(f)
    assert v1_1_meta["revid"] != v1_revid  # validate absence of -o option
    assert v1_1_meta["size"] == 16  # validate no newline at end in storage


def test_validate_metadata(index_create2):
    moin_dir, _ = get_dirs("")
    data_dir = moin_dir / "src" / "moin" / "cli" / "_tests" / "data"
    item_put = run(["moin", "item-put", "-m", data_dir / "MyPage-v1.meta", "-d", data_dir / "MyPage-v1.data", "-o"])
    assert_p_succcess(item_put)
    sleep(1.1)  # MTIME is stored as int in index file, sleep here to guarntee proper sorting of revs for index_revision
    item_put = run(["moin", "item-put", "-m", data_dir / "MyPage-v2.meta", "-d", data_dir / "MyPage-v2.data", "-o"])
    assert_p_succcess(item_put)
    validate = run(["moin", "maint-validate-metadata", "-b", "default", "-v"])
    assert_p_succcess(validate)
    outlines = validate.stdout.splitlines()
    assert 1 == len(outlines)
    assert b"0 items with invalid metadata found" == outlines[0]
    item_put = run(["moin", "item-put", "-m", data_dir / "Corrupt.meta", "-d", data_dir / "Corrupt.data", "-o"])
    assert_p_succcess(item_put)
    sleep(1.1)  # MTIME is stored as int in index file, sleep here to guarntee proper sorting of revs for index_revision
    item_put = run(["moin", "item-put", "-m", data_dir / "Corrupt2.meta", "-d", data_dir / "Corrupt2.data", "-o"])
    assert_p_succcess(item_put)
    sleep(1.1)  # MTIME is stored as int in index file, sleep here to guarntee proper sorting of revs for index_revision
    item_put = run(["moin", "item-put", "-m", data_dir / "Corrupt3.meta", "-d", data_dir / "Corrupt3.data", "-o"])
    assert_p_succcess(item_put)
    validate = run(["moin", "maint-validate-metadata", "-b", "default", "-v"])
    assert_p_succcess(validate)
    outlines = validate.stdout.decode().splitlines()
    assert 4 == len(outlines)
    rev_id1 = "7ed018d7ceda49409e18b8efb914f5ff"  # Corrupt.meta
    rev_id2 = "0a2f1b476b6c42be80908b3b799df3fd"  # Corrupt2.meta
    rev_id3 = "39c8fe8da0a048c0b7839bf8aa02cd04"  # Corrupt3.meta
    rev_id4 = "484e73725601407e9f9ab0bcaa151fb6"  # MyPage-v1.meta
    rev_id5 = "b0b07c407c3143aabc4d34aac1b1d303"  # MyPage-v2.meta
    outlines_by_rev_id = {}
    for outline in outlines:
        words = iter(outline.split())
        for word in words:
            if word == "rev_id:":
                outlines_by_rev_id[next(words)] = outline
                break
    assert {rev_id1, rev_id2, rev_id3} == set(outlines_by_rev_id.keys())
    assert (
        "size_error name: Home item: cbd6fc46f88740acbc1dca90bb1eb8f3 rev_number: 1 rev_id: 7ed018d7ceda49409e18b8efb914f5ff "
        "meta_size: 8 real_size: 11" == outlines_by_rev_id[rev_id1]
    )
    assert (
        "sha1_error name: Page2 item: 9999989aca5e45cc8683432f986a0e50 rev_number: 1 rev_id: 0a2f1b476b6c42be80908b3b799df3fd "
        "meta_sha1: 25ff6d28976a9e0feb97710a0c4b08ae197a0000 "
        "real_sha1: 25ff6d28976a9e0feb97710a0c4b08ae197afbfe" == outlines_by_rev_id[rev_id2]
    )
    assert (
        "parentid_error name: Page3 item: 3c7e36466726441faf6d7d266ac224e2 rev_number: 2 rev_id: 39c8fe8da0a048c0b7839bf8aa02cd04 "
        "meta_parentid: 002e5210cc884010b0dd75a1c337032d correct_parentid: None meta_revision_number: 2"
        == outlines_by_rev_id[rev_id3]
    )
    assert "3 items with invalid metadata found" == outlines[3]
    validate = run(["moin", "maint-validate-metadata", "-b", "default", "-f"])
    assert_p_succcess(validate)
    outlines = validate.stdout.splitlines()
    assert 1 == len(outlines)
    assert b"3 items with invalid metadata found and fixed" == outlines[0]
    validate = run(["moin", "maint-validate-metadata", "-b", "default", "-v"])
    assert_p_succcess(validate)
    outlines = validate.stdout.splitlines()
    assert 1 == len(outlines)
    assert b"0 items with invalid metadata found" == outlines[0]
    # validate index is updated
    index_dump = run(["moin", "index-dump", "--no-truncate"])
    metas = {m[REVID]: m for m in read_index_dump(index_dump.stdout.decode())}
    assert {rev_id1, rev_id2, rev_id3, rev_id4, rev_id5} == set(metas.keys())
    assert 11 == metas[rev_id1][SIZE]
    assert PARENTID not in metas[rev_id3]
    # create a repeated revision_number
    sleep(1.1)  # MTIME is stored as int in index file, sleep here to guarntee proper sorting of revs for index_revision
    item_put = run(["moin", "item-put", "-m", data_dir / "MyPage-v2.meta", "-d", data_dir / "MyPage-v2.data"])
    assert_p_succcess(item_put)
    validate = run(["moin", "maint-validate-metadata", "-b", "default", "-v", "-f"])
    assert_p_succcess(validate)
    outlines = validate.stdout.decode().splitlines()
    assert "1 items with invalid metadata found and fixed" == outlines[-1]
    assert 3 == len(outlines)
    outlines_by_error = {}
    for outline in outlines[0:2]:
        words = outline.split()
        outlines_by_error[words[0]] = outline
    assert {"parentid_error", "revision_number_error"} == set(outlines_by_error.keys())
    index_dump = run(["moin", "index-dump", "--no-truncate"])
    rev_numbers = {m[REV_NUMBER]: m for m in read_index_dump(index_dump.stdout.decode()) if m[NAMES] == "MyPage"}
    assert {1, 2, 3} == set(rev_numbers.keys())
    assert rev_numbers[1][REVID] == rev_id4
    assert rev_numbers[2][REVID] == rev_id5


def test_validate_metadata_missing_rev_num(index_create2):
    moin_dir, _ = get_dirs("")
    data_dir = moin_dir / "src" / "moin" / "cli" / "_tests" / "data"
    item_put = run(["moin", "item-put", "-m", data_dir / "MyPage-vblank.meta", "-d", data_dir / "MyPage-v1.data", "-o"])
    assert_p_succcess(item_put)
    sleep(1.1)  # MTIME is stored as int in index file, sleep here to guarntee proper sorting of revs for index_revision
    item_put = run(
        ["moin", "item-put", "-m", data_dir / "MyPage-vblank2.meta", "-d", data_dir / "MyPage-v1.data", "-o"]
    )
    assert_p_succcess(item_put)
    validate = run(["moin", "maint-validate-metadata", "-b", "default", "-v", "-f"])
    assert_p_succcess(validate)
    index_dump = run(["moin", "index-dump", "--no-truncate"])
    print(index_dump.stdout.decode())
    rev_numbers = {m[REV_NUMBER]: m for m in read_index_dump(index_dump.stdout.decode()) if m[NAMES] == "MyPage"}
    assert {1, 2} == set(rev_numbers.keys())
