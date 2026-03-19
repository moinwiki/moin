# Copyright: 2026 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

import logging

from moin.log import getLogger
from moin.converters import ConverterMessage

logger = getLogger(__name__)


class ConverterBase:

    def __init__(self) -> None:
        self.messages: set[ConverterMessage] = set()

    def log(self, message: str, category: str) -> None:
        self.messages.add(ConverterMessage(message, category))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Converter message: <<{message}>>; category={category}")

    def reset_messages(self) -> None:
        self.messages.clear()
