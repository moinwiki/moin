# Copyright: 2025 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.dump_html tests
"""

import pytest

from pathlib import Path

from moin.cli._tests import assert_p_succcess, run
from moin.cli.maint.dump_html import fixup_item_content


@pytest.mark.parametrize(
    "item_name, input, expected",
    [
        # raw data link with text content
        (
            "page1",
            '<a href="/+get/+f896c691fd9b42cab5884f911e43777e/magic">Pure magic</a>',
            '<a href="+get/magic.raw" download="magic">Pure magic</a>',
        ),
        # raw data link to video content
        (
            "demo/page2",
            '<video controls="controls" src="/+get/+f896c691fd9b42cab5884f911e43777e/help-common/video.mp4">Unsupported</video>',
            '<video controls="controls" src="../+get/help-common/video.mp4" download="video.mp4">Unsupported</video>',
        ),
    ],
)
def test_fixup_item_links(item_name: str, input: str, expected: str) -> None:
    output = fixup_item_content(item_name, input)
    assert output == expected


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
