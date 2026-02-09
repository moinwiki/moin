# Copyright: 2004 Oliver Graf <ograf@bitart.de>
# Copyright: 2007 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.utils.pysupport.
"""

import os
import errno

import pytest

from flask import current_app as app

from moin.utils import pysupport, crypto
from moin.utils import plugins


class TestImportNameFromMoin:
    """Tests importName for MoinMoin modules.

    We do not test files here, assuming that the moin package is not broken.
    """

    def test_non_existing_module(self):
        """pysupport: import nonexistent module raises ImportError"""
        pytest.raises(ImportError, pysupport.importName, "moin.utils.nonexistent", "importName")

    def test_non_existing_attribute(self):
        """pysupport: import nonexistent attribute raises AttributeError"""
        pytest.raises(AttributeError, pysupport.importName, "moin.utils.pysupport", "nonexistent")

    def test_existing(self):
        """pysupport: import name from existing module"""
        from moin.utils.pysupport import importName

        t = pysupport.importName("moin.utils.pysupport", "importName")
        assert importName is t


@pytest.mark.usefixtures("_app_ctx", "custom_setup")
class TestImportNameFromPlugin:
    """Base class for import plugin tests"""

    name = "Parser"

    @pytest.fixture
    def custom_setup(self):
        """Check for valid plugin package"""
        self.pluginDirectory = os.path.join(app.cfg.data_dir, "plugin", "parser")
        self.checkPackage(self.pluginDirectory)

    def checkPackage(self, path):
        for item in (path, os.path.join(path, "__init__.py")):
            if not os.path.exists(item):
                pytest.skip(f"Missing or wrong permissions: {item}")

    def pluginExists(self):
        return os.path.exists(self.pluginFilePath(".py")) or os.path.exists(self.pluginFilePath(".pyc"))

    def pluginFilePath(self, suffix):
        return os.path.join(self.pluginDirectory, self.plugin + suffix)


class TestImportNonExisting(TestImportNameFromPlugin):

    plugin = "NonExistingWikiPlugin"

    def test_non_existing(self):
        """pysupport: import nonexistent wiki plugin fails"""
        if self.pluginExists():
            pytest.skip(f"plugin exists: {self.plugin}")
        pytest.raises(plugins.PluginMissingError, plugins.importWikiPlugin, app.cfg, "parser", self.plugin, "Parser")


class TestImportExisting(TestImportNameFromPlugin):

    plugin = "AutoCreatedMoinMoinTestPlugin"
    shouldDeleteTestPlugin = True

    @pytest.mark.usefixtures("_app_ctx")
    def test_existing(self):
        """pysupport: import existing wiki plugin

        Tests whether a module can be imported from an arbitrary path,
        as done in moin for plugins. A bug in the old implementation
        failed on an import of os because os performs a 'from os.path import',
        which would stumble over a poisoned sys.modules.
        """
        try:
            self.createTestPlugin()
            # clear the plugin cache...
            app.cfg._site_plugin_lists = {}
            parser = plugins.importWikiPlugin(app.cfg, "parser", self.plugin, "Parser")
            assert getattr(parser, "__name__", None) == "Parser"
            assert parser.key == self.key
        finally:
            self.deleteTestPlugin()

    def createTestPlugin(self):
        """Create test plugin, skipping if plugin exists"""
        if self.pluginExists():
            self.shouldDeleteTestPlugin = False
            pytest.skip(f"Won't overwrite existing plugin: {self.plugin}")
        self.key = crypto.random_string(32, "abcdefg")
        data = """
# If you find this file in your wiki plugin directory, you can safely
# delete it.
import sys, os

class Parser:
    key = '{}'
""".format(self.key)
        try:
            open(self.pluginFilePath(".py"), "w").write(data)
        except Exception as err:
            pytest.skip(f"Can't create test plugin: {err!s}")

    def deleteTestPlugin(self):
        """Delete plugin files, ignoring missing-file errors"""
        if not self.shouldDeleteTestPlugin:
            return
        for suffix in (".py", ".pyc"):
            try:
                os.unlink(self.pluginFilePath(suffix))
            except OSError as err:
                if err.errno != errno.ENOENT:
                    raise


coverage_modules = ["moin.utils.pysupport"]
