# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli base tests

tests for cli defined in moin/cli/__init__.py
"""

from moin.cli._tests import run


def test_moin(artifact_dir):
    moin_p = run(['moin'])
    assert moin_p.returncode == 0
    assert moin_p.stdout.startswith(b"Quick help")


def test_moin_help(artifact_dir):
    moin_p = run(['moin', 'help'])
    assert moin_p.returncode == 0
    assert moin_p.stdout.startswith(b"Quick help")


def test_moin_dash_dash_help(artifact_dir):
    moin_p = run(['moin', '--help'])
    assert moin_p.returncode == 0
    assert moin_p.stdout.startswith(b"Usage: moin")
