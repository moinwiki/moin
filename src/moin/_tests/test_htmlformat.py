# Copyright: 2026 MoinMoin contributors
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.htmlformat tests.

Covers the HTML source pretty-printer used to make "view source" readable
(see issue #297) and the after_request handler that applies it to text/html
responses.
"""

from __future__ import annotations

import pytest
from flask import Response

from moin.apps.frontend.views import format_html_source
from moin.utils.htmlformat import BLOCK_TAGS, RAW_TEXT_TAGS, format_html


class TestFormatHtml:
    def test_block_tags_get_newlines(self):
        assert format_html("<div><p>hi</p></div>") == "<div>\n<p>hi\n</p>\n</div>"

    def test_nested_structure(self):
        html = "<html><head><title>t</title></head><body><div>d</div></body></html>"
        assert format_html(html) == (
            "<html>\n<head><title>t</title>\n</head>\n<body>\n<div>d\n</div>\n</body>\n</html>"
        )

    def test_inline_content_untouched(self):
        html = "a <b>x</b> b <a href='u'>link</a> c"
        assert format_html(html) == html

    def test_adjacent_block_tags_separated(self):
        assert format_html("<ul><li>one<li>two</ul>") == "<ul>\n<li>one\n<li>two\n</ul>"

    def test_pre_content_verbatim(self):
        html = "<div><pre>line1\n  line2 <b>not-a-tag</b></pre></div>"
        assert format_html(html) == "<div>\n<pre>line1\n  line2 <b>not-a-tag</b></pre>\n</div>"

    def test_script_content_verbatim(self):
        # the "<" inside the script must not be treated as a tag
        html = "<script>if (a<b) { c(); }</script><p>after</p>"
        assert format_html(html) == "<script>if (a<b) { c(); }</script>\n<p>after\n</p>"

    def test_textarea_content_verbatim(self):
        html = "<textarea>a<b</textarea><p>x</p>"
        assert format_html(html) == "<textarea>a<b</textarea>\n<p>x\n</p>"

    def test_style_content_verbatim(self):
        html = "<style>a>b { color: red; }</style><p>x</p>"
        assert format_html(html) == "<style>a>b { color: red; }</style>\n<p>x\n</p>"

    def test_comment_verbatim(self):
        html = "<div><!-- a <b> comment --><span>s</span></div>"
        assert format_html(html) == "<div><!-- a <b> comment --><span>s</span>\n</div>"

    def test_empty_and_plain_text(self):
        assert format_html("") == ""
        assert format_html("just text") == "just text"

    def test_existing_newlines_not_duplicated(self):
        html = "<div>\n<p>hi</p>\n</div>"
        # no blank lines are introduced; the close tag still moves to its own line
        assert format_html(html) == "<div>\n<p>hi\n</p>\n</div>"
        assert "\n\n" not in format_html(html)

    def test_no_leading_newline_added(self):
        assert not format_html("<div>x</div>").startswith("\n")

    @pytest.mark.parametrize("tag", sorted(BLOCK_TAGS - RAW_TEXT_TAGS))
    def test_all_block_tags_break(self, tag):
        # every block tag gets a newline before its open tag when preceded by text
        out = format_html(f"x<{tag}>y</{tag}>")
        assert out == f"x\n<{tag}>y\n</{tag}>", tag

    @pytest.mark.parametrize("tag", sorted(BLOCK_TAGS & RAW_TEXT_TAGS))
    def test_block_raw_text_tags_break_but_content_verbatim(self, tag):
        # pre/textarea are block-level, so a newline goes before them, but
        # their whole content (including the close tag) is copied verbatim
        out = format_html(f"x<{tag}>y\nz</{tag}>")
        assert out == f"x\n<{tag}>y\nz</{tag}>", tag

    @pytest.mark.parametrize("tag", sorted(RAW_TEXT_TAGS))
    def test_raw_text_tags_copied_verbatim(self, tag):
        html = f"<div><{tag}>  a<b\n c  </{tag}></div>"
        out = format_html(html)
        assert f"<{tag}>  a<b\n c  </{tag}>" in out, tag

    def test_idempotent(self):
        html = (
            "<html><head><title>t</title><script>if(a<b){}</script></head>"
            "<body><div class='x'><p>hi <b>there</b></p><pre>keep\n this</pre>"
            "<!-- note --></div></body></html>"
        )
        once = format_html(html)
        assert format_html(once) == once

    def test_unclosed_tag_at_end(self):
        assert format_html("<div>text <span") == "<div>text <span"

    def test_unclosed_comment(self):
        assert format_html("<div><!-- oops") == "<div><!-- oops"


class TestFormatHtmlSourceHandler:
    """The after_request handler in moin.apps.frontend.views."""

    def test_html_response_is_formatted(self):
        resp = Response("<div><p>hi</p></div>", mimetype="text/html")
        result = format_html_source(resp)
        assert result.get_data(as_text=True) == "<div>\n<p>hi\n</p>\n</div>"

    def test_html_with_charset_is_formatted(self):
        resp = Response("<div><p>hi</p></div>", content_type="text/html; charset=utf-8")
        result = format_html_source(resp)
        assert result.get_data(as_text=True) == "<div>\n<p>hi\n</p>\n</div>"
        assert result.mimetype == "text/html"

    def test_json_response_untouched(self):
        resp = Response('{"a": "<div>"}', mimetype="application/json")
        result = format_html_source(resp)
        assert result.get_data(as_text=True) == '{"a": "<div>"}'

    def test_plain_text_untouched(self):
        resp = Response("<div>not html</div>", mimetype="text/plain")
        result = format_html_source(resp)
        assert result.get_data(as_text=True) == "<div>not html</div>"

    def test_streamed_response_untouched(self):
        def gen():
            yield "<div><p>hi</p></div>"

        resp = Response(gen(), mimetype="text/html")
        assert resp.is_streamed
        result = format_html_source(resp)
        assert result.is_streamed
        assert result.get_data(as_text=True) == "<div><p>hi</p></div>"

    def test_handler_registered_on_frontend_blueprint(self):
        from moin.apps.frontend import frontend

        assert format_html_source in frontend.after_request_funcs.get(None, [])

    def test_handler_end_to_end_via_after_request_chain(self):
        # run the handler through a real Flask after_request chain
        from flask import Flask

        mini = Flask(__name__)
        mini.after_request(format_html_source)

        @mini.route("/")
        def index():
            return Response("<div><p>hi</p></div>", mimetype="text/html")

        @mini.route("/json")
        def json_view():
            return Response('{"a": "<div>"}', mimetype="application/json")

        client = mini.test_client()
        resp = client.get("/")
        assert resp.mimetype == "text/html"
        assert resp.get_data(as_text=True) == "<div>\n<p>hi\n</p>\n</div>"
        resp = client.get("/json")
        assert resp.get_data(as_text=True) == '{"a": "<div>"}'
