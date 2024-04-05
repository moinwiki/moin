# Copyright: 2002 Juergen Hermann <jh@web.de>
# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Supporting functions for Python magic
"""

import os
import sys
import re
import importlib


#############################################################################
# Module import / Plugins
#############################################################################


def load_package_modules(package_name, package_pathes):
    """
    Load (import) all modules from some package (except those starting with _).

    This is useful if there is some code in the module that runs at import time
    and registers some code of that module somewhere.

    Call this from __init__.py of the same package like this:

        load_package_modules(__name__, __path__)
    """
    assert isinstance(package_pathes, (list, tuple))
    for path in package_pathes:
        for fname in os.listdir(path):
            if fname.endswith(".py") and not fname.startswith("_"):
                module = package_name + "." + fname[:-3]
                if module not in sys.modules:
                    importlib.import_module(module)


def isImportable(module):
    """Check whether a certain module is available."""
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
    """Return a list of modules for a package, omitting any modules
    starting with an underscore.
    """
    packagedir = os.path.dirname(packagefile)
    dirlist = os.listdir(packagedir)
    pyre = re.compile(r"^([^_].*)\.py$")
    matches = [pyre.match(fn) for fn in dirlist]
    modules = sorted([match.group(1) for match in matches if match])
    return modules


def importName(modulename, name):
    """Import name dynamically from module

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
    """Call with a function you want to make thread safe

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


class AutoNe:
    """
    Implement __ne__ in terms of __eq__. This is a mixin class.
    """

    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is NotImplemented:
            return ret
        return not ret
