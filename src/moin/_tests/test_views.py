"""
    MoinMoin - moin.views Tests
"""

from moin.apps.frontend.views import parse_scoped_query


class TestParseScopedQuery:
    def test_parse_scoped_query_with_prefix_and_query(self):
        scope, actual_query = parse_scoped_query(">Lectures design patterns")
        assert scope == "Lectures"
        assert actual_query == "design patterns"

    def test_parse_scoped_query_with_prefix_only(self):
        scope, actual_query = parse_scoped_query(">Lectures")
        assert scope == "Lectures"
        assert actual_query == ""

    def test_parse_scoped_query_without_prefix(self):
        scope, actual_query = parse_scoped_query("design patterns")
        assert scope is None
        assert actual_query == "design patterns"

    def test_parse_scoped_query_empty(self):
        scope, actual_query = parse_scoped_query("")
        assert scope is None
        assert actual_query == ""
