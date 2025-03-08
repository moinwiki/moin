# Copyright: 2025 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.dump_html tests
"""

from pathlib import Path

from moin.cli._tests import assert_p_succcess, run


def create_instance():
    return run(["moin", "create-instance"])


def index_create():
    return run(["moin", "index-create"])


def welcome():
    return run(["moin", "welcome"])


def dump_html(html_dir):
    return run(["moin", "dump-html", "--directory", str(html_dir)])


def test_dump_html(moin_test_dir: Path) -> None:
    assert_p_succcess(create_instance())
    assert_p_succcess(index_create())
    assert_p_succcess(welcome())
    html_dir = moin_test_dir / "html"
    assert_p_succcess(dump_html(html_dir))
    assert html_dir.exists()
