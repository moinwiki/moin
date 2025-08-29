# Copyright: 2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Arguments wrapper.
"""


class Arguments:
    """
    Represent an argument list that may contain positional and keyword arguments.
    """

    __slots__ = "positional", "keyword"

    def __init__(self, positional=None, keyword=None):
        self.positional = positional and positional[:] or []
        self.keyword = keyword and keyword.copy() or {}

    def __contains__(self, key):
        """
        Check for the presence of a positional argument or a keyword key.
        """
        return key in self.positional or key in self.keyword

    def __getitem__(self, key):
        """
        Access positional arguments by index or keyword arguments by key name.
        """
        if isinstance(key, (int, slice)):
            return self.positional[key]
        return self.keyword[key]

    def __len__(self):
        """
        Total count of positional + keyword args.
        """
        return len(self.positional) + len(self.keyword)

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.positional!r}, {self.keyword!r})>"

    def items(self):
        """
        Return an iterator over all (key, value) pairs.
        Positional arguments are assumed to have a None key.
        """
        for value in self.positional:
            yield None, value
        yield from self.keyword.items()

    def keys(self):
        """
        Return an iterator over all keys from the keyword arguments.
        """
        yield from self.keyword.keys()

    def values(self):
        """
        Return an iterator over all values.
        """
        yield from self.positional
        yield from self.keyword.values()
