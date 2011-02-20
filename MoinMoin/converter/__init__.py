"""
MoinMoin - Converter support

Converters are used to convert between formats or between different featuresets
of one format.

There are usually three types of converters:
- Between an input format like Moin Wiki or Creole and the internal tree
  representation.
- Between the internal tree and an output format like HTML.
- Between different featuresets of the internal tree representation like URI
  types or macro expansion.

TODO: Merge with new-style macros.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from ..util.registry import RegistryBase


class RegistryConverter(RegistryBase):
    class Entry(object):
        def __init__(self, factory, type_input, type_output, priority):
            self.factory = factory
            self.type_input = type_input
            self.type_output = type_output
            self.priority = priority

        def __call__(self, type_input, type_output, kw):
            if (self.type_output.issupertype(type_output) and
                    self.type_input.issupertype(type_input)):
                    return self.factory(type_input, type_output, **kw)

        def __eq__(self, other):
            if isinstance(other, self.__class__):
                return (self.factory == other.factory and
                        self.type_input == other.type_input and
                        self.type_output == other.type_output and
                        self.priority == other.priority)
            return NotImplemented

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                if self.priority < other.priority:
                    return True
                if self.type_output != other.type_output:
                    if other.type_output.issupertype(self.type_output):
                        return True
                    return False
                if self.type_input != other.type_input:
                    if other.type_input.issupertype(self.type_input):
                        return True
                    return False
                return False
            return NotImplemented

        def __repr__(self):
            return '<%s: input %s, output %s, prio %d [%r]>' % (self.__class__.__name__,
                    self.type_input,
                    self.type_output,
                    self.priority,
                    self.factory)

    def get(self, type_input, type_output, **kw):
        for entry in self._entries:
            conv = entry(type_input, type_output, kw)
            if conv is not None:
                return conv

    def register(self, factory, type_input, type_output, priority=RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        @param factory: Factory to register. Callable, must return an object
        """
        return self._register(self.Entry(factory, type_input, type_output, priority))


# TODO: Move somewhere else. Also how to do that for per-wiki modules?
def _load():
    import imp, os, sys
    for path in __path__:
        for root, dirs, files in os.walk(path):
            del dirs[:]
            for file in files:
                if file.startswith('_') or not file.endswith('.py'):
                    continue
                module = file[:-3]
                module_complete = __name__ + '.' + module
                if module_complete in sys.modules:
                    continue
                info = imp.find_module(module, [root])
                try:
                    try:
                        imp.load_module(module_complete, *info)
                    except Exception, e:
                        import MoinMoin.log as logging
                        logger = logging.getLogger(__name__)
                        logger.exception("Failed to import converter package %s: %s" % (module, e))
                finally:
                    info[0].close()

default_registry = RegistryConverter()
_load()
