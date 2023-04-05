# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.create_instance tests
"""


def test_create_instance(artifact_dir, create_instance):
    assert (artifact_dir / 'wikiconfig.py').exists()
    assert (artifact_dir / 'intermap.txt').exists()
    assert (artifact_dir / 'wiki_local').exists()
