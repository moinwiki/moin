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


from collections import namedtuple

from ..utils.registry import RegistryBase
from ..utils.pysupport import load_package_modules


class ElementException(RuntimeError):
    pass


class RegistryConverter(RegistryBase):
    class Entry(namedtuple("Entry", "factory type_input type_output priority")):
        def __call__(self, type_input, type_output, **kw):
            if self.type_output.issupertype(type_output) and self.type_input.issupertype(type_input):
                return self.factory(type_input, type_output, **kw)

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                if self.type_output != other.type_output:
                    return other.type_output.issupertype(self.type_output)
                if self.type_input != other.type_input:
                    return other.type_input.issupertype(self.type_input)
                if self.priority != other.priority:
                    return self.priority < other.priority
                return False
            return NotImplemented

    def register(self, factory, type_input, type_output, priority=RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        :param factory: Factory to register. Callable, must return an object.
        """
        return self._register(self.Entry(factory, type_input, type_output, priority))


default_registry = RegistryConverter()
load_package_modules(__name__, __path__)
