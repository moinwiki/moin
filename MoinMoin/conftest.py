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
collect_ignore = ['static',  # same
                  '../wiki', # no tests there
                  '../instance', # tw likes to use this for wiki data (non-revisioned)
                 ]

import atexit
import os
import sys
import inspect

import py

from MoinMoin.app import create_app_ext, destroy_app, before_wiki, after_wiki
from MoinMoin._tests import maketestwiki, wikiconfig
from MoinMoin.storage.backends import create_simple_mapping

coverage_modules = set()

try:
    """
    This code adds support for coverage.py (see
    http://nedbatchelder.com/code/modules/coverage.html).
    It prints a coverage report for the modules specified in all
    module globals (of the test modules) named "coverage_modules".
    """

    import coverage

    def report_coverage():
        coverage.stop()
        module_list = sorted([sys.modules[mod] for mod in coverage_modules])
        coverage.report(module_list)

    def callback(option, opt_str, value, parser):
        atexit.register(report_coverage)
        coverage.erase()
        coverage.start()

    def pytest_addoption(parser):
        group = parser.getgroup('MoinMoin options')
        group.addoption(
            '-C', '--coverage',
            action='callback', callback=callback,
            help='Output information about code coverage (slow!)')

except ImportError:
    coverage = None



def init_test_app(given_config):
    namespace_mapping, router_index_uri = create_simple_mapping("memory:", given_config.content_acl)
    more_config = dict(
        namespace_mapping=namespace_mapping,
        router_index_uri=router_index_uri,
    )
    app = create_app_ext(flask_config_dict=dict(SECRET_KEY='foobarfoobar'),
                         moin_config_class=given_config,
                         **more_config)
    ctx = app.test_request_context('/')
    ctx.push()
    before_wiki()
    return app, ctx

def deinit_test_app(app, ctx):
    after_wiki('')
    ctx.pop()
    destroy_app(app)


class MoinClassCollector(py.test.collect.Class):

    def setup(self):
        cls = self.obj
        if hasattr(cls, 'Config'):
            given_config = cls.Config
        else:
            given_config = wikiconfig.Config

        def setup_method(f):
            def wrapper(self, *args, **kwargs):
                # Important: FIRST init the test app, then call the wrapped function.
                self.app, self.ctx = init_test_app(given_config)
                # Don't forget to call the class' setup_method if it has one.
                return f(self, *args, **kwargs)
            return wrapper

        def teardown_method(f):
            def wrapper(self, *args, **kwargs):
                # Don't forget to call the class' teardown_method if it has one.
                # Important: FIRST call the wrapped function, so it can still
                # access the stuff removed by deinit_test_app:
                ret = f(self, *args, **kwargs)
                deinit_test_app(self.app, self.ctx)
                return ret
            return wrapper

        try:
            # Wrap the actual setup_method in our decorator.
            cls.setup_method = setup_method(cls.setup_method)
        except AttributeError:
            # Perhaps the test class did not define a setup_method.
            def no_setup(self, method):
                self.app, self.ctx = init_test_app(given_config)
            cls.setup_method = no_setup

        try:
            # Wrap the actual teardown_method in our decorator.
            cls.teardown_method = teardown_method(cls.teardown_method)
        except AttributeError:
            # Perhaps the test class did not define a teardown_method.
            def no_teardown(self, method):
                deinit_test_app(self.app, self.ctx)
            cls.teardown_method = no_teardown

        super(MoinClassCollector, self).setup()

    def teardown(self):
        super(MoinClassCollector, self).teardown()


def pytest_pycollect_makemodule(path, parent):
    return Module(path, parent=parent)

def pytest_pycollect_makeitem(__multicall__, collector, name, obj):
    if collector.classnamefilter(name) and inspect.isclass(obj):
        return MoinClassCollector(name, parent = collector)

def pytest_report_header(config):
    return "The tests here are implemented only for pytest-2"

class Module(py.test.collect.Module):
    Class = MoinClassCollector

    def run(self, *args, **kwargs):
        if coverage is not None:
            coverage_modules.update(getattr(self.obj, 'coverage_modules', []))
        return super(Module, self).run(*args, **kwargs)

