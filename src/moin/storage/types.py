# Copyright: 2025 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from io import BufferedReader, BytesIO
from typing import Any, TypeAlias

Document = dict[str, Any]
"""A indexer document"""

MetaData: TypeAlias = dict[str, Any]

ItemData: TypeAlias = BufferedReader | BytesIO

ValidationState: TypeAlias = dict[str, Any]
"""Type of the validatation state passed into flatland metadata validation"""
