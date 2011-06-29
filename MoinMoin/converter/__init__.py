# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

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
"""


from ..util.registry import RegistryBase
from ..util.pysupport import load_package_modules


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
                    return other.type_output.issupertype(self.type_output)
                if self.type_input != other.type_input:
                    return other.type_input.issupertype(self.type_input)
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

        :param factory: Factory to register. Callable, must return an object.
        """
        return self._register(self.Entry(factory, type_input, type_output, priority))


default_registry = RegistryConverter()
load_package_modules(__name__, __path__)

