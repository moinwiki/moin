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
i = 0
import atexit
import os
import sys
import inspect

import pytest

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


class MoinTestFunction(pytest.collect.Function):
    def setup(self):
        if inspect.isclass(self.parent.obj.__class__):
            cls = self.parent.obj.__class__
        if hasattr(cls, 'Config'):
            given_config = cls.Config
        else:
            given_config = wikiconfig.Config
        
        self.app, self.ctx = init_test_app(given_config)

        super(MoinTestFunction, self).setup()
        #XXX: hack till we get better funcarg tools
        self._obj.im_self.app = self.app

    def teardown(self):
        super(MoinTestFunction, self).teardown()
        deinit_test_app(self.app, self.ctx)
        

    
    # Need to modify and add more stuffs    
    
    
def pytest_pycollect_makemodule(path, parent):
    return Module(path, parent=parent)

def pytest_pycollect_makeitem(__multicall__, collector, name, obj):
    if collector.funcnamefilter(name) and inspect.isfunction(obj):
        return MoinTestFunction(name, parent = collector)

"""hook to intercept generators and run them as a single test items"""       
def pytest_pyfunc_call(pyfuncitem):
    if inspect.isgeneratorfunction(pyfuncitem.obj):
        for item in pyfuncitem.obj():
            kwarg = item[1:]
            item[0](*kwarg)           

def pytest_report_header(config):
    return "The tests here are implemented only for pytest-2"

class Module(pytest.collect.Module):
    def run(self, *args, **kwargs):
        if coverage is not None:
            coverage_modules.update(getattr(self.obj, 'coverage_modules', []))
        return super(Module, self).run(*args, **kwargs)

