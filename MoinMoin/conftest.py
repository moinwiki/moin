# Copyright: 2005 MoinMoin:NirSoffer
# Copyright: 2007 MoinMoin:AlexanderSchremmer
# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin Testing Framework
--------------------------

All test modules must be named test_modulename to be included in the
test suite. If you are testing a package, name the test module
test_package_module.

Tests that require a certain configuration, like section_numbers = 1, must
use a Config class to define the required configuration within the test class.
"""


from __future__ import absolute_import, division

# exclude some directories from py.test test discovery, pathes relative to this file
collect_ignore = [
    'static',  # same
    '../wiki',  # no tests there
    '../instance',  # tw likes to use this for wiki data (non-revisioned)
]

import pytest
import py
import MoinMoin.log
import MoinMoin

# Logging for tests to avoid useless output like timing information on stderr on test failures
Moindir = py.path.local(MoinMoin.__file__).dirname
config_file = Moindir + '/_tests/test_logging.conf'
MoinMoin.log.load_config(config_file)

from MoinMoin.app import create_app_ext, destroy_app, before_wiki, teardown_wiki
from MoinMoin._tests import wikiconfig
from MoinMoin.storage import create_simple_mapping


@pytest.fixture
def cfg():
    return wikiconfig.Config


@pytest.yield_fixture
def app_ctx(cfg):
    namespace_mapping, backend_mapping, acl_mapping = create_simple_mapping(
        "stores:memory:",
        cfg.default_acl
    )
    more_config = dict(
        namespace_mapping=namespace_mapping,
        backend_mapping=backend_mapping,
        acl_mapping=acl_mapping,
        create_storage=True,  # create a fresh storage at each app start
        destroy_storage=True,  # kill all storage contents at app shutdown
        create_index=True,  # create a fresh index at each app start
        destroy_index=True,  # kill index contents at app shutdown
    )
    app = create_app_ext(
        flask_config_dict=dict(SECRET_KEY='foobarfoobar'),
        moin_config_class=cfg,
        **more_config
    )
    ctx = app.test_request_context('/', base_url="http://localhost:8080/")
    ctx.push()
    before_wiki()

    yield app, ctx

    teardown_wiki('')
    ctx.pop()
    destroy_app(app)


@pytest.fixture(autouse=True)
def app(app_ctx):
    return app_ctx[0]


def pytest_pycollect_makemodule(path, parent):
    return Module(path, parent=parent)


def pytest_report_header(config):
    return "The tests here are implemented only for pytest-2"


class Module(pytest.collect.Module):
    def run(self, *args, **kwargs):
        if coverage is not None:
            coverage_modules.update(getattr(self.obj, 'coverage_modules', []))
        return super(Module, self).run(*args, **kwargs)
