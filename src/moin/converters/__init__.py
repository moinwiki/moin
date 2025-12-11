# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Converter support

Converters are used to convert between formats or between different feature sets
of one format.

There are usually three types of converters:

- Between an input format like MoinWiki or Creole and the internal tree
  representation.
- Between the internal tree and an output format like HTML.
- Between different feature sets of the internal tree representation like URI
  types or macro expansion.

TODO: Merge with new-style macros.
"""

from __future__ import annotations

from typing import Any, Callable, NamedTuple, Protocol, TYPE_CHECKING

from ..utils.registry import RegistryBase
from ..utils.pysupport import load_package_modules

if TYPE_CHECKING:
    from moin.utils.mime import Type


class ElementException(RuntimeError):
    pass


class Converter(Protocol):
    def __call__(self, *args: Any, **kwargs) -> Any | None: ...


class RegistryConverter(RegistryBase[Converter]):

    class Entry(NamedTuple):
        factory: Callable[[Type, Type], Converter | None]
        type_input: Type
        type_output: Type
        priority: int

        def __call__(self, type_input: Type, type_output: Type, **kwargs) -> Converter | None:
            if self.type_output.issupertype(type_output) and self.type_input.issupertype(type_input):
                return self.factory(type_input, type_output, **kwargs)
            return None

        def __lt__(self, other: Any):
            if isinstance(other, self.__class__):
                if self.type_output != other.type_output:
                    return other.type_output.issupertype(self.type_output)
                if self.type_input != other.type_input:
                    return other.type_input.issupertype(self.type_input)
                if self.priority != other.priority:
                    return self.priority < other.priority
                return False
            return NotImplemented

    def register(
        self,
        factory: Callable[..., Converter | None],
        type_input: Type,
        type_output: Type,
        priority: int = RegistryBase.PRIORITY_MIDDLE,
    ) -> None:
        """
        Register a factory.

        :param factory: Factory to register. Callable; must return an object.
        """
        self._register(self.Entry(factory, type_input, type_output, priority))


default_registry = RegistryConverter()
load_package_modules(__name__, __path__)
