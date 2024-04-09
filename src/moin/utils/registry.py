# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Module registry

Every module registers a factory for itself at the registry with a given
priority.  During the lookup each factory is called with the given arguments and
can return a callable to consider itself as a match.
"""


from collections import namedtuple


class RegistryBase:
    PRIORITY_REALLY_FIRST = -20
    PRIORITY_FIRST = -10
    PRIORITY_MIDDLE = 0
    PRIORITY_LAST = 10
    PRIORITY_REALLY_LAST = 20

    class Entry(namedtuple("Entry", "factory priority")):
        def __call__(self, *args, **kw):
            return self.factory(*args, **kw)

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                return self.priority < other.priority
            return NotImplemented

    def __init__(self):
        self._entries = []

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self._entries!r}>"

    def get(self, *args, **kw):
        """
        Lookup a matching module

        Each registered factory is called with the given arguments and
        the first matching wins.
        """
        for entry in self._entries:
            conv = entry(*args, **kw)
            if conv is not None:
                return conv

    def _register(self, entry):
        if entry not in self._entries:
            entries = self._entries[:]
            for i in range(len(entries)):
                if entry < entries[i]:
                    entries.insert(i, entry)
                    break
            else:
                entries.append(entry)
            self._entries = entries

    def unregister(self, factory):
        """
        Unregister a factory

        :param factory: Factory to unregister
        """
        old_entries = self._entries
        entries = [i for i in old_entries if i.factory is not factory]
        if len(old_entries) == len(entries):
            # TODO: Is this necessary?
            raise ValueError
        self._entries = entries


class Registry(RegistryBase):
    def register(self, factory, priority=RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        :param factory: Factory to register. Callable, have to return a class
        """
        return self._register(self.Entry(factory, priority))
