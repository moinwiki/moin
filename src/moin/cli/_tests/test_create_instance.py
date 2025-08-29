# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.cli.maint.create_instance.
"""

from moin.cli._tests import assert_p_succcess


def test_create_instance(artifact_dir, create_instance):
    assert_p_succcess(create_instance)
    assert (artifact_dir / "wikiconfig.py").exists()
    assert (artifact_dir / "intermap.txt").exists()
    assert (artifact_dir / "wiki_local").exists()
