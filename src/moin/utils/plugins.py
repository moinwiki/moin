# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2004 by Florian Festi
# Copyright: 2006 by Mikko Virkkil
# Copyright: 2005-2010 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:ReimarBauer
# Copyright: 2008 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - plugin loader
"""


import os
import sys
import importlib
import hashlib

from moin import error
from moin.utils import pysupport
from moin.utils.mimetype import MimeType


class PluginError(Exception):
    """Base class for plugin errors"""


class PluginMissingError(PluginError):
    """Raised when a plugin is not found"""


class PluginAttributeError(PluginError):
    """Raised when plugin does not contain an attribtue"""


def importPlugin(cfg, kind, name, function="execute"):
    """Import wiki or builtin plugin

    Returns <function> attr from a plugin module <name>.
    If <function> attr is missing, raise PluginAttributeError.
    If <function> is None, return the whole module object.

    If <name> plugin can not be imported, raise PluginMissingError.

    kind may be one of 'action', 'macros' or any other
    directory that exist in MoinMoin or data/plugin.

    Wiki plugins will always override builtin plugins. If you want
    specific plugin, use either importWikiPlugin or importBuiltinPlugin
    directly.

    :param cfg: wiki config instance
    :param kind: what kind of module we want to import
    :param name: the name of the module
    :param function: the function name
    :rtype: any object
    :returns: "function" of module "name" of kind "kind", or None
    """
    try:
        return importWikiPlugin(cfg, kind, name, function)
    except PluginMissingError:
        return importBuiltinPlugin(kind, name, function)


def importWikiPlugin(cfg, kind, name, function="execute"):
    """Import plugin from the wiki data directory

    See importPlugin docstring.
    """
    plugins = wikiPlugins(kind, cfg)
    modname = plugins.get(name, None)
    if modname is None:
        raise PluginMissingError()
    moduleName = f"{modname}.{name}"
    return importNameFromPlugin(moduleName, function)


def importBuiltinPlugin(kind, name, function="execute"):
    """Import builtin plugin from MoinMoin package

    See importPlugin docstring.
    """
    if name not in builtinPlugins(kind):
        raise PluginMissingError()
    moduleName = f"moin.{kind}.{name}"
    return importNameFromPlugin(moduleName, function)


def importNameFromPlugin(moduleName, name):
    """Return <name> attr from <moduleName> module,
    raise PluginAttributeError if name does not exist.

    If name is None, return the <moduleName> module object.
    """
    if name is None:
        fromlist = []
    else:
        fromlist = [name]
    module = __import__(moduleName, globals(), {}, fromlist)
    if fromlist:
        # module has the obj for module <moduleName>
        try:
            return getattr(module, name)
        except AttributeError:
            raise PluginAttributeError
    else:
        # module now has the toplevel module of <moduleName> (see __import__ docs!)
        components = moduleName.split(".")
        for comp in components[1:]:
            module = getattr(module, comp)
        return module


def builtinPlugins(kind):
    """Gets a list of modules in moin.'kind'

    :param kind: what kind of modules we look for
    :rtype: list
    :returns: module names
    """
    modulename = "moin." + kind
    return pysupport.importName(modulename, "modules")


def wikiPlugins(kind, cfg):
    """
    Gets a dict containing the names of all plugins of <kind>
    as the key and the containing module name as the value.

    :param kind: what kind of modules we look for
    :rtype: dict
    :returns: plugin name to containing module name mapping
    """
    # short-cut if we've loaded the dict already
    # (or already failed to load it)
    cache = cfg._site_plugin_lists
    if kind in cache:
        result = cache[kind]
    else:
        result = {}
        for modname in cfg._plugin_modules:
            try:
                module = pysupport.importName(modname, kind)
                packagepath = os.path.dirname(module.__file__)
                plugins = pysupport.getPluginModules(packagepath)
                for p in plugins:
                    if p not in result:
                        result[p] = f"{modname}.{kind}"
            except AttributeError:
                pass
        cache[kind] = result
    return result


def getPlugins(kind, cfg):
    """Gets a list of plugin names of kind

    :param kind: what kind of modules we look for
    :rtype: list
    :returns: module names
    """
    # Copy names from builtin plugins - so we dont destroy the value
    all_plugins = builtinPlugins(kind)[:]

    # Add extension plugins without duplicates
    for plugin in wikiPlugins(kind, cfg):
        if plugin not in all_plugins:
            all_plugins.append(plugin)

    return all_plugins


def searchAndImportPlugin(cfg, type, name, what=None):
    type2classname = {}
    if what is None:
        what = type2classname[type]
    mt = MimeType(name)
    plugin = None
    for module_name in mt.module_name():
        try:
            plugin = importPlugin(cfg, type, module_name, what)
            break
        except PluginMissingError:
            pass
    else:
        raise PluginMissingError(f"Plugin not found! ({type!r} {name!r} {what!r})")
    return plugin


@pysupport.makeThreadSafe
def _loadPluginModule(cfg):
    """
    import all plugin modules

    To be able to import plugin from arbitrary path, we have to load the base
    package. Later, we can use standard mechanisms to load plugins in this package.

    Since each configured plugin path has unique plugins, we load the plugin
    packages as "moin_p_<sha1(path)>".
    """
    assert isinstance(cfg.plugin_dirs, (list, tuple))
    cfg._plugin_modules = []
    for pdir in cfg.plugin_dirs:
        assert isinstance(pdir, str)
        modname = "moin_p_{}".format(hashlib.new("sha1", pdir.encode()).hexdigest())
        if modname not in sys.modules:
            init_path = os.path.join(os.path.abspath(pdir), "__init__.py")
            spec = importlib.util.spec_from_file_location(modname, init_path)
            if spec is not None:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[modname] = module
            else:
                msg = """\
Could not import plugin package "%(path)s":

Make sure your data directory path is correct, check permissions, and
that the data/plugin directory has an __init__.py file.
""" % dict(
                    path=pdir
                )
                raise error.ConfigurationError(msg)
        if modname not in cfg._plugin_modules:
            cfg._plugin_modules.append(modname)
