# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Text highlighting converter.

The highlight pattern comes from the user-controlled ?regex= query parameter.
To protect against ReDoS, plain search words are matched literally and all
matching for one document shares a time budget (the stdlib re module can not
be interrupted, so the third-party regex module is used for its timeout).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import time

import regex as re

from moin.converters.base import ConverterBase
from moin.log import getLogger
from moin.utils.mime import type_moin_document
from moin.utils.tree import html, moin_page

from . import default_registry

if TYPE_CHECKING:
    from moin.utils.mime import Type
    from typing_extensions import Self

logger = getLogger(__name__)

# Maximum total time (in seconds) spent on matching the highlight pattern within one document.
HIGHLIGHT_TIMEOUT = 0.5


class Converter(ConverterBase):

    @classmethod
    def _factory(cls, input: Type, output: Type, highlight: str = "", regex: str = "", **kwargs: Any) -> Self | None:
        return cls(regex, **kwargs) if highlight == "highlight" else None

    def __init__(self, regex: str, timeout: float = HIGHLIGHT_TIMEOUT, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.timeout = timeout
        self.deadline = 0.0
        self.pattern: Any  # compiled regex.Pattern or None
        try:
            if match := re.fullmatch('r"([^"]*)"', regex):
                # extract the real regex from Whoosh regex search term
                pattern = match.group(1)
                flags = 0
            else:
                # treat each word separately as literal text and ignore case sensitivity
                pattern = "|".join(re.escape(word) for word in regex.split())
                flags = re.IGNORECASE
            # an empty pattern would only produce empty matches, highlighting nothing
            self.pattern = re.compile(pattern, flags) if pattern else None
        except re.error:
            # regex is user-controlled via ?regex= query param; an invalid
            # pattern must not break the view, it should just match nothing.
            self.pattern = None

    def __call__(self, tree: Any) -> Any:
        if self.pattern is not None:
            self.deadline = time.monotonic() + self.timeout
            self.recurse(tree)
        return tree

    def recurse(self, elem):
        new_childs = []

        for child in elem:
            if isinstance(child, (bytes, str)):
                # Restrict it to our own namespace for now.
                if self.pattern is not None and elem.tag.uri == moin_page.namespace:
                    new_childs.extend(self.highlight(child))
                else:
                    new_childs.append(child)
            else:
                self.recurse(child)
                new_childs.append(child)

        # Use inline replacement to avoid a complete tree copy
        if len(new_childs) > len(elem):
            elem[:] = new_childs

    def highlight(self, text):
        """
        Return the list of child nodes replacing text: the parts of text matching the pattern
        get wrapped into highlighting elements, the rest is kept as is.

        If the time budget is exhausted, return text unchanged and stop highlighting.
        """
        assert self.pattern is not None
        new_childs = []
        pos = 0
        try:
            for match in self.pattern.finditer(text, timeout=max(self.deadline - time.monotonic(), 0.0)):
                start, end = match.span()
                if start == end:
                    continue  # nothing visible to highlight
                new_childs.append(text[pos:start])
                attrib = {html.class_: "moin-highlight"}
                new_childs.append(moin_page.strong(attrib=attrib, children=[text[start:end]]))
                pos = end
        except TimeoutError:
            logger.warning("highlighting aborted, pattern %r took too long", self.pattern.pattern)
            self.pattern = None
            return [text]
        new_childs.append(text[pos:])
        return new_childs


default_registry.register(Converter._factory, type_moin_document, type_moin_document)
