# Copyright: 2026 NOQT
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""Tests for the Pygments input converter."""

import pytest

from moin.converters.pygments_in import Converter
from moin.utils.tree import moin_page


@pytest.mark.parametrize(
    "text, expected_class",
    [
        ("<article>one line</article>", "highlight wrap"),
        ("<article>one line</article>\n", "highlight wrap"),
        ("<article>\n    <para>indented</para>\n</article>\n", "highlight"),
    ],
)
def test_wrap_class_for_single_line_content(text, expected_class):
    doc = Converter(contenttype="application/docbook+xml")(text)

    blockcode = doc[0][0]

    assert blockcode.get(moin_page.class_) == expected_class
