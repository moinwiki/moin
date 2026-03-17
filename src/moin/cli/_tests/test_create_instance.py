# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.cli.maint.create_instance.
"""

from moin.cli._tests import assert_p_succcess


def test_create_instance(artifacts_dir, create_instance):
    assert_p_succcess(create_instance)
    assert (artifacts_dir / "wikiconfig.py").exists()
    assert (artifacts_dir / "intermap.txt").exists()
    assert (artifacts_dir / "wiki_local").exists()
