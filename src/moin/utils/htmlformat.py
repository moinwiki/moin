# Copyright: 2026 MoinMoin contributors
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Pretty-print generated HTML source.

Moin's templates emit long runs of tags on a single line, which makes the
page source hard to read in "view source". This module inserts line breaks
around *block-level* elements only — inline content, text and the contents of
``pre``/``textarea``/``script``/``style`` are never touched, so rendering is
unchanged while the source gains one element per line.
"""

from __future__ import annotations

import re

# Elements that start a new line in rendering: a newline next to them is
# invisible in the rendered page, so it is safe to add one in the source.
BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "caption",
        "dd",
        "details",
        "dialog",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hgroup",
        "hr",
        "html",
        "body",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)

# Elements whose content is raw text: never insert anything inside them.
RAW_TEXT_TAGS = frozenset({"pre", "textarea", "script", "style"})

_TAG_NAME_RE = re.compile(r"</?([a-zA-Z][a-zA-Z0-9-]*)")


def format_html(html: str) -> str:
    """
    Insert newlines before block-level open tags and after block-level close
    tags, leaving everything else (text, inline tags, comments, raw-text
    element contents) byte-for-byte intact. Idempotent.
    """
    parts: list[str] = []
    i = 0
    n = len(html)
    prev = ""  # last character emitted, so repeated runs add no extra newlines
    while i < n:
        lt = html.find("<", i)
        if lt == -1:
            parts.append(html[i:])
            break
        text = html[i:lt]
        parts.append(text)
        if text:
            prev = text[-1]
        if html.startswith("<!--", lt):
            # Copy comments verbatim.
            end = html.find("-->", lt)
            end = n if end == -1 else end + 3
            parts.append(html[lt:end])
            prev = html[end - 1]
            i = end
            continue
        gt = html.find(">", lt)
        if gt == -1:
            parts.append(html[lt:])
            break
        token = html[lt : gt + 1]
        match = _TAG_NAME_RE.match(token)
        name = match.group(1).lower() if match else ""
        if name in RAW_TEXT_TAGS and not token.startswith("</"):
            # Copy the whole raw-text element, content included, verbatim.
            if name in BLOCK_TAGS and prev and prev != "\n":
                parts.append("\n")
                prev = "\n"
            close = re.compile(rf"</{name}\s*>", re.IGNORECASE).search(html, gt + 1)
            end = close.end() if close else n
            parts.append(html[lt:end])
            prev = html[end - 1]
            i = end
            continue
        if name in BLOCK_TAGS:
            if prev and prev != "\n":
                parts.append("\n")
            parts.append(token)
            prev = token[-1]
            if token.startswith("</") and gt + 1 < n and html[gt + 1] != "\n":
                parts.append("\n")
                prev = "\n"
            i = gt + 1
            continue
        parts.append(token)
        prev = token[-1]
        i = gt + 1
    return "".join(parts)
