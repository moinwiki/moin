# Copyright: 2004 Oliver Graf <ograf@bitart.de>
# Copyright: 2007 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.pysupport Tests
"""


import os, errno

import py

from flask import current_app as app

from MoinMoin.util import pysupport, crypto
from MoinMoin.util import plugins


class TestImportNameFromMoin(object):
    """ Test importName of MoinMoin modules

    We don't make any testing for files, assuming that moin package is
    not broken.
    """

    def testNonExistingModule(self):
        """ pysupport: import nonexistent module raises ImportError """
        py.test.raises(ImportError, pysupport.importName,
                       'MoinMoin.util.nonexistent', 'importName')

    def testNonExistingAttribute(self):
        """ pysupport: import nonexistent attritbue raises AttributeError """
        py.test.raises(AttributeError, pysupport.importName,
                       'MoinMoin.util.pysupport', 'nonexistent')

    def testExisting(self):
        """ pysupport: import name from existing module """
        from MoinMoin.util.pysupport import importName
        t = pysupport.importName('MoinMoin.util.pysupport', 'importName')
        assert importName is t


class TestImportNameFromPlugin(object):
    """ Base class for import plugin tests """

    name = 'Parser'

    def setup_method(self, method):
        """ Check for valid plugin package """
        self.pluginDirectory = os.path.join(app.cfg.data_dir, 'plugin', 'parser')
        self.checkPackage(self.pluginDirectory)

    def checkPackage(self, path):
        for item in (path, os.path.join(path, '__init__.py')):
            if not os.path.exists(item):
                py.test.skip("Missing or wrong permissions: %s" % item)

    def pluginExists(self):
        return (os.path.exists(self.pluginFilePath('.py')) or
                os.path.exists(self.pluginFilePath('.pyc')))

    def pluginFilePath(self, suffix):
        return os.path.join(self.pluginDirectory, self.plugin + suffix)


class TestImportNonExisting(TestImportNameFromPlugin):

    plugin = 'NonExistingWikiPlugin'

    def testNonExisting(self):
        """ pysupport: import nonexistent wiki plugin fail """
        if self.pluginExists():
            py.test.skip('plugin exists: %s' % self.plugin)
        py.test.raises(plugins.PluginMissingError,
                       plugins.importWikiPlugin,
                           app.cfg, 'parser',
                           self.plugin, 'Parser')


class TestImportExisting(TestImportNameFromPlugin):

    plugin = 'AutoCreatedMoinMoinTestPlugin'
    shouldDeleteTestPlugin = True

    def testExisting(self):
        """ pysupport: import existing wiki plugin

        Tests if a module can be imported from an arbitrary path
        like it is done in moin for plugins. Some strange bug
        in the old implementation failed on an import of os,
        cause os does a from os.path import that will stumble
        over a poisoned sys.modules.
        """
        try:
            self.createTestPlugin()
            # clear the plugin cache...
            app.cfg._site_plugin_lists = {}
            parser = plugins.importWikiPlugin(app.cfg, 'parser',
                                               self.plugin, 'Parser')
            assert getattr(parser, '__name__', None) == 'Parser'
            assert parser.key == self.key
        finally:
            self.deleteTestPlugin()

    def createTestPlugin(self):
        """ Create test plugin, skiping if plugin exists """
        if self.pluginExists():
            self.shouldDeleteTestPlugin = False
            py.test.skip("Won't overwrite existing plugin: %s" % self.plugin)
        self.key = crypto.random_string(32, 'abcdefg')
        data = '''
# If you find this file in your wiki plugin directory, you can safely
# delete it.
import sys, os

class Parser:
    key = '%s'
''' % self.key
        try:
            file(self.pluginFilePath('.py'), 'w').write(data)
        except Exception as err:
            py.test.skip("Can't create test plugin: %s" % str(err))

    def deleteTestPlugin(self):
        """ Delete plugin files ignoring missing files errors """
        if not self.shouldDeleteTestPlugin:
            return
        for suffix in ('.py', '.pyc'):
            try:
                os.unlink(self.pluginFilePath(suffix))
            except OSError as err:
                if err.errno != errno.ENOENT:
                    raise

coverage_modules = ['MoinMoin.util.pysupport']
