# Copyright: 2002 Juergen Hermann <jh@web.de>
# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Supporting functions for Python magic
"""

import os
import sys
import re
import imp


#############################################################################
### Module import / Plugins
#############################################################################

def load_package_modules(package_name, package_pathes):
    """
    Load (import) all modules from some package (except those starting with _).

    This is useful if there is some code in the module that runs at import time
    and registers some code of that module somewhere.

    Call this from __init__.py of the same package like this:

        load_package_modules(__name__, __path__)
    """
    for path in package_pathes:
        for root, dirs, files in os.walk(path):
            del dirs[:]
            for fname in files:
                if fname.startswith('_') or not fname.endswith('.py'):
                    continue
                module = fname[:-3]
                module_complete = package_name + '.' + module
                if module_complete in sys.modules:
                    continue
                info = imp.find_module(module, [root])
                try:
                    try:
                        imp.load_module(module_complete, *info)
                    except Exception as e:
                        import MoinMoin.log as logging
                        logger = logging.getLogger(package_name)
                        logger.exception("Failed to import {0} package module {1}: {2}".format(package_name, module, e))
                finally:
                    info[0].close()


def isImportable(module):
    """ Check whether a certain module is available.
    """
    try:
        __import__(module)
        return 1
    except ImportError:
        return 0


def getPluginModules(packagedir):
    """
    Return a list of plugin modules for a given plugin package dir,
    omitting any that start with an underscore.
    """
    pyre = re.compile(r"^([^_].*)\.py$")
    dirlist = os.listdir(packagedir)
    matches = [pyre.match(fn) for fn in dirlist]
    modules = sorted([match.group(1) for match in matches if match])

    return modules


def getPackageModules(packagefile):
    """ Return a list of modules for a package, omitting any modules
        starting with an underscore.
    """
    packagedir = os.path.dirname(packagefile)

    in_plugin_dir = lambda dir, ops=os.path.split: ops(ops(dir)[0])[1] == "plugin"

    moinmodule = __import__('MoinMoin')

    # Is it in a .zip file?
    if not in_plugin_dir(packagedir) and hasattr(moinmodule, '__loader__'):
        pyre = re.compile(r"^([^_].*)\.py(?:c|o)$")
        zipfiles = moinmodule.__loader__._files
        dirlist = [entry[0].replace(r'/', '\\').split('\\')[-1]
                   for entry in zipfiles.values() if packagedir in entry[0]]
    else:
        pyre = re.compile(r"^([^_].*)\.py$")
        dirlist = os.listdir(packagedir)

    matches = [pyre.match(fn) for fn in dirlist]
    modules = sorted([match.group(1) for match in matches if match])

    return modules


def importName(modulename, name):
    """ Import name dynamically from module

    Used to do dynamic import of modules and names that you know their
    names only in runtime.

    Any error raised here must be handled by the caller.

    :param modulename: full qualified mudule name, e.g. x.y.z
    :param name: name to import from modulename
    :rtype: any object
    :returns: name from module
    """
    module = __import__(modulename, globals(), {}, [name])
    return getattr(module, name)


def makeThreadSafe(function, lock=None):
    """ Call with a function you want to make thread safe

    Call without lock to make the function thread safe using one lock per
    function. Call with existing lock object if you want to make several
    functions use same lock, e.g. all functions that change same data
    structure.

    :param function: function to make thread safe
    :param lock: threading.Lock instance or None
    :rtype: function
    :returns: function decorated with locking
    """
    if lock is None:
        import threading
        lock = threading.Lock()

    def decorated(*args, **kw):
        lock.acquire()
        try:
            return function(*args, **kw)
        finally:
            lock.release()

    return decorated


class AutoNe(object):
    """
    Implement __ne__ in terms of __eq__. This is a mixin class.
    """
    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is NotImplemented:
            return ret
        return not ret
