# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.modify_item tests
"""

import json
import os
from pathlib import Path

from moin._tests import get_dirs
from moin.cli._tests import run


def validate_meta(expected, actual):
    for d in expected, actual:
        del d['address']  # remove elements which may not match
        del d['mtime']
    assert expected == actual


def test_load_help(load_help):
    assert load_help[0].returncode == 0
    assert load_help[1].returncode == 0


def test_dump_help(load_help):
    moin_dir, artifact_dir = get_dirs('cli')
    help_dir = artifact_dir / 'my_help'
    help_common_dir = help_dir / 'common'
    if not help_common_dir.exists():
        help_common_dir.mkdir(parents=True)
    dash_p = os.path.relpath(help_dir, moin_dir / 'src' / 'moin' / 'cli' / 'maint')
    dump_help = run(['moin', 'dump-help', '-n', 'common', '-p', dash_p])
    assert dump_help.returncode == 0
    data_file_names = help_common_dir.glob('*.data')
    source_help_dir = moin_dir / 'help' / 'common'
    expected_data_file_names = source_help_dir.glob('*.data')
    assert expected_data_file_names, data_file_names
    for data_file_name in data_file_names:
        with open(help_common_dir / data_file_name, 'rb') as f:
            data = f.read()
        with open(source_help_dir / data_file_name, 'rb') as f:
            expected_data = f.read()
        assert expected_data == data, f'{data_file_name} in dump not matching to source'
        meta_file_name = f'{str(data_file_name)[0:-5]}.meta'
        with open(help_common_dir / meta_file_name) as f:
            meta = json.load(f)
        with open(source_help_dir / meta_file_name) as f:
            expected_meta = json.load(f)
        validate_meta(expected_meta, meta)


def test_item_get(load_help):
    """extract an item from help and validate data and meta match original files in moin/help"""
    item_get = run(['moin', 'item-get', '-n', 'help-common/cat.jpg', '-m', 'cat.meta', '-d', 'cat.data'])
    assert item_get.returncode == 0
    assert Path('cat.data').exists()
    assert Path('cat.meta').exists()
    moin_dir, _ = get_dirs('cli')
    with open('cat.meta') as f:
        meta_cat = json.load(f)
    with open(moin_dir / 'src' / 'moin' / 'help' / 'common' / 'cat.jpg.meta') as f:
        meta_cat_expected = json.load(f)
    validate_meta(meta_cat_expected, meta_cat)
    with open('cat.data', 'rb') as f:
        cat_bytes = f.read()
    with open(moin_dir / 'src' / 'moin' / 'help' / 'common' / 'cat.jpg.data', 'rb') as f:
        cat_bytes_expected = f.read()
    assert cat_bytes_expected == cat_bytes


def test_item_put(index_create):
    """validate ability to add a new item to the wiki via item-put and extract using item-get"""
    item_get_fail = run(['moin', 'item-get', '-n', 'Home', '-m', 'Home.meta', '-d', 'Home.data'])
    assert item_get_fail.returncode != 0
    item_get_fail = run(['moin', 'item-get', '-n', 'help-common/Home', '-m', 'help-common-Home.meta', '-d', 'help-common-Home.data'])
    assert item_get_fail.returncode != 0
    moin_dir, _ = get_dirs('cli')
    data_dir = moin_dir / 'src' / 'moin' / 'cli' / '_tests' / 'data'
    item_put = run(['moin', 'item-put', '-m', data_dir / 'Home.meta', '-d', data_dir / 'Home.data'])
    assert item_put.returncode == 0
    item_put = run(['moin', 'item-put', '-m', data_dir / 'help-common-Home.meta', '-d', data_dir / 'help-common-Home.data'])
    assert item_put.returncode == 0
    item_get = run(['moin', 'item-get', '-n', 'Home', '-m', 'Home.meta', '-d', 'Home.data'])
    assert item_get.returncode == 0
    item_get = run(['moin', 'item-get', '-n', 'help-common/Home', '-m', 'help-common-Home.meta', '-d', 'help-common-Home.data'])
    assert item_get.returncode == 0


def test_item_rev(index_create2):
    """test loading multiple versions of same page

    validate -o option when present, revid in meta file is retained otherwise new revid is generated

    validate handling of newline at end of file

    *  MyPage-v1 does not have newline at end in storage (size = 16)
    *  MyPage-v2 has newline at end in storage (size = 18)
    *  in both cases, item-get will write file with os.linesep at end of file"""
    moin_dir, _ = get_dirs('cli2')
    data_dir = moin_dir / 'src' / 'moin' / 'cli' / '_tests' / 'data'
    put1 = run(['moin', 'item-put', '-m', data_dir / 'MyPage-v1.meta', '-d', data_dir / 'MyPage-v1.data', '-o'])
    assert put1.returncode == 0
    put2 = run(['moin', 'item-put', '-m', data_dir / 'MyPage-v2.meta', '-d', data_dir / 'MyPage-v2.data', '-o'])
    assert put2.returncode == 0
    item_get2 = run(['moin', 'item-get', '-n', 'MyPage', '-m', 'MyPage-v2.meta', '-d', 'MyPage-v2.data'])
    assert item_get2.returncode == 0
    with open('MyPage-v2.data', newline='') as f:
        assert f.read() == f'MyPage version 2{os.linesep}'
    with open('MyPage-v2.meta') as f:
        v2_meta = json.load(f)
    assert v2_meta['size'] == 18  # newline at end is 2 chars \r\n
    with open(data_dir / 'MyPage-v1.meta') as f:
        v1_meta = json.load(f)
    v1_revid = v1_meta['revid']
    assert v1_meta['size'] == 16
    item_get1 = run(['moin', 'item-get', '-n', 'MyPage', '-m', 'MyPage-v1.meta', '-d', 'MyPage-v1.data', '-r', v1_revid])
    assert item_get1.returncode == 0
    with open('MyPage-v1.data', newline='') as f:
        assert f.read() == f'MyPage version 1{os.linesep}'
    put3 = run(['moin', 'item-put', '-m', 'MyPage-v1.meta', '-d', 'MyPage-v1.data'])
    assert put3.returncode == 0
    item_get1_1 = run(['moin', 'item-get', '-n', 'MyPage', '-m', 'MyPage-v1_1.meta', '-d', 'MyPage-v1_1.data'])
    assert item_get1_1.returncode == 0
    with open('MyPage-v1_1.data', newline='') as f:
        assert f.read() == f'MyPage version 1{os.linesep}'
    with open('MyPage-v1_1.meta') as f:
        v1_1_meta = json.load(f)
    assert v1_1_meta['revid'] != v1_revid  # validate absence of -o option
    assert v1_1_meta['size'] == 16  # validate no newline at end in storage
