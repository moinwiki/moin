# Copyright: 2026 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import Any, cast

import logging

from moin.log import getLogger
from moin.converters import ConverterMessage
from moin.converters._util import _Stack

logger = getLogger(__name__)


class ConverterBase:

    def __init__(self, **kwargs: Any) -> None:
        self.messages: set[ConverterMessage] = set()
        self.add_lineno = cast(bool, kwargs.get("add_lineno", False))

    def make_stack(self, bottom=None, iter_content=None) -> _Stack:
        return _Stack(bottom, iter_content, self.add_lineno)

    def log(self, message: str, category: str) -> None:
        self.messages.add(ConverterMessage(message, category))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Converter message: <<{message}>>; category={category}")

    def reset_messages(self) -> None:
        self.messages.clear()
