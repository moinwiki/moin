# Copyright: 2025 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import Any
from dataclasses import dataclass, field


@dataclass
class RenderContext:
    preview: Any = None
    allow_style_attributes: bool = True
    convert_inline_style: bool = False
    use_nonces: bool = False
    extra_args: dict[str, Any] = field(default_factory=dict)
    css_classes: dict[str, str] = field(default_factory=dict)
    result: str | None = None
    # messages: list[ConverterMessage] = field(default_factory=list)
