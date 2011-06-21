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

import pytest
import py
import MoinMoin.log

""" Logging for tests to avoid useless output like timing information on stderr on test failures
"""
Moindir = py.path.local(__file__).dirname
config_file = Moindir + '/test_logging.conf'
MoinMoin.log.load_config(config_file)

from MoinMoin.app import create_app_ext, destroy_app, before_wiki, after_wiki
from MoinMoin._tests import maketestwiki, wikiconfig
from MoinMoin.storage.backends import create_simple_mapping

#In the beginning following variables have no values
prev_app = None
prev_cls = None
prev_ctx = None

def get_previous(self_app, self_ctx, cls):
    prev_app = self_app
    prev_ctx = self_ctx
    prev_cls = cls
    return prev_app, prev_ctx, prev_cls

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
    try:
        def setup(self):
            if inspect.isclass(self.parent.obj.__class__):
                cls = self.parent.obj.__class__

                # global variables so that previous values can be accessed            
                global prev_app, prev_ctx, prev_cls

                if hasattr(cls, 'Config'):
                    if prev_app != None:
                        # deinit previous app if previous app value is not None.
                        deinit_test_app(prev_app, prev_ctx)
                    given_config = cls.Config
                    # init app
                    self.app, self.ctx = init_test_app(given_config)
                else:
                    given_config = wikiconfig.Config
                    # deinit the previous app if previous class had its own configuration
                    # deinit the previous app if the class of previous function has an attribute 'create_backend' 
                    # this is for the tests of storage module until we use some cleanup mechanism on tests.
                    if hasattr(prev_cls, 'Config') or hasattr(prev_cls, 'create_backend'):
                        deinit_test_app(prev_app, prev_ctx)
                        print "problem is here"        
                    # Initialize the app in following two conditions: 
                    # 1. It is the first test item 
                    # 2. Class of previous function item had its own configuration i.e. hasattr(cls, Config)
                    # Also if the Class of previous function is having an attribute as 'create_backend', 
                    # this is for the tests of storage module until we use some cleanup mechanism on tests.
                    if prev_app == None or hasattr(prev_cls, 'Config') or hasattr(prev_cls, 'create_backend'):
                        self.app, self.ctx = init_test_app(given_config)
                    # continue assigning the values of the previous app and ctx to the current ones.
                    else:
                        self.app = prev_app
                        self.ctx = prev_ctx    

                #Get the values from the function
                prev_app, prev_ctx, prev_cls = get_previous(self.app, self.ctx, cls)

            else:
                prev_app, prev_ctx, prev_cls = get_previous(None, None, None)            

            super(MoinTestFunction, self).setup()
            #XXX: hack till we get better funcarg tools
            if hasattr(self._obj, 'im_self'):
                self._obj.im_self.app = self.app

    finally:
        def teardown(self):
            super(MoinTestFunction, self).teardown()
        
    # Need to modify and add more stuffs    
    
    
def pytest_pycollect_makemodule(path, parent):
    return Module(path, parent=parent)

def pytest_pycollect_makeitem(__multicall__, collector, name, obj):
    if collector.funcnamefilter(name) and inspect.isfunction(obj):
        return MoinTestFunction(name, parent = collector)

def pytest_pyfunc_call(pyfuncitem):
    """hook to intercept generators and run them as a single test items"""       
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

