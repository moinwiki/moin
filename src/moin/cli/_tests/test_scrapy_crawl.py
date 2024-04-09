# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli._tests.test_scrapy_crawl

crawl moin site and report on errors"""

import pytest

try:
    from moin.cli._tests import settings
except ImportError:
    from moin.cli._tests import default_settings as settings
from moin.cli._tests.scrapy.moincrawler.items import CrawlResultMatch
from moin.cli._tests.conftest import get_crawl_log_path
from moin.utils.iri import Iri
from moin import log

logging = log.getLogger(__name__)


class TestSiteCrawl:
    EXPECTED_404 = [
        CrawlResultMatch(
            url_path_components=["MissingSubItem", "MissingSubitem", "MissingPage", "MissingItem", "MissingSibling"]
        )
    ]
    KNOWN_ISSUES = [
        CrawlResultMatch(
            url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST, path="/+get/help-common/logo.png"),
            from_url="/markdown",
        ),  # only with wiki_root
        CrawlResultMatch(
            url="http://localhost:8080/+serve/ckeditor/plugins/smiley/images/shades_smile.gif", from_url="/html"
        ),
        CrawlResultMatch(
            url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST, path="/users/Home"), from_url="/html"
        ),  # only with wiki_root
    ]
    line_number = 0
    line_buffer = []
    gathered_log_lines = {}

    @staticmethod
    def _matches_one_of(r, matches):
        for m in matches:
            if m.match(r):
                return True
        return False

    def is_known_issue(self, r):
        return self._matches_one_of(r, self.KNOWN_ISSUES)

    def is_expected_404(self, r):
        return self._matches_one_of(r, self.EXPECTED_404)

    def test_home_page(self, crawl_results):
        assert crawl_results[1], f"crawl failed, check {get_crawl_log_path()}"
        for line in open(get_crawl_log_path(), "rb"):
            if b"crawl.csv" in line:
                logging.info(f"{line} from {get_crawl_log_path()}")
        assert len(crawl_results[0]) > 0
        r = crawl_results[0][0]
        expected = CrawlResultMatch(url="/Home")
        assert expected.match(r), f"unexpected redirect for / {r}"

    def test_200(self, crawl_results):
        assert crawl_results[1], f"crawl failed, check {get_crawl_log_path()}"
        failures = []
        for r in [
            r
            for r in crawl_results[0]
            if r.url and r.url.authority == settings.SITE_HOST and not self.is_known_issue(r)
        ]:
            if "Discussion" in r.url.path:
                expected = {200, 404}
            elif self.is_expected_404(r):
                expected = {404}
            else:
                expected = {200}
            if r.response_code not in expected:
                failures.append(r)
                logging.error(f"expected {expected} got {r.response_code} for {r}")
        assert len(failures) == 0

    @pytest.mark.xfail(reason="issue #1414 - remaining bad links in help")
    def test_expected_failures(self, crawl_results):
        assert crawl_results[1], f"crawl failed, check {get_crawl_log_path()}"
        failures = []
        for r in [r for r in crawl_results[0] if self.is_known_issue(r)]:
            if r.response_code != 200:
                logging.info(f"known issue {r}")
                failures.append(r)
        assert len(failures) == 0

    @pytest.mark.skip
    def test_known_issues_exist(self, crawl_results):
        """enable this test to check for KNOWN_ISSUES which can be removed
        after removing, be sure to confirm by crawling a host with non-blank SITE_WIKI_ROOT
        as some issues only exist when moin is running behind apache"""
        assert crawl_results[1], f"crawl failed, check {get_crawl_log_path()}"
        fixed = []
        for m in self.KNOWN_ISSUES:
            seen = False
            my_fixed = []
            my_not_fixed = []
            for r in [r for r in crawl_results[0] if m.match(r)]:
                seen = True
                if r.response_code == 200:
                    my_fixed.append(r)
                else:
                    my_not_fixed.append(r)
            if not my_not_fixed:
                for r in my_fixed:
                    logging.error(f"{r} matching {m} is fixed")
                    fixed.append((m, r))
            if not seen:
                logging.error(f"match {m} not seen")
                fixed.append((m, None))
        assert len(fixed) == 0

    def test_valid_request(self, crawl_results):
        assert crawl_results[1], f"crawl failed, check {get_crawl_log_path()}"
        failures = []
        for r in [r for r in crawl_results[0] if not self.is_known_issue(r)]:
            if not r.response_code:
                logging.error(f"no response code for {r}")
                failures.append(r)
        assert len(failures) == 0

    def _gather_current_log_line(self):
        for line_number_buffer, line_from_buffer in self.line_buffer:
            self.gathered_log_lines[line_number_buffer] = line_from_buffer
        self.line_buffer = []

    def _next_server_log_line(self):
        try:
            self.line = next(self.server_log)
        except StopIteration:
            return False
        self.line_number += 1
        while len(self.line_buffer) >= 3:
            self.line_buffer.pop(0)
        self.line_buffer.append((self.line_number, self.line))
        return True

    def test_server_log(self, server_crawl_log):
        """validate no ERROR nor Traceback in log

        see https://github.com/moinwiki/moin/pull/1399"""
        with open(server_crawl_log) as self.server_log:
            trailing_line_count = 0
            is_traceback = False
            prev_gather = False
            error_count = 0
            while self._next_server_log_line():
                # when error line is seen, print including traceback block with two leading and two trailing lines
                start_traceback = "Traceback" in self.line
                is_error = " ERROR " in self.line
                if is_error or start_traceback:
                    error_count += 1
                if not is_traceback:
                    is_traceback = start_traceback
                gather = is_traceback or is_error
                if gather:
                    trailing_line_count = 0
                if trailing_line_count:
                    trailing_line_count += 1
                    if trailing_line_count > 3:
                        trailing_line_count = 0
                if prev_gather and (not gather):
                    trailing_line_count = 1
                prev_gather = gather
                if gather or trailing_line_count:
                    self._gather_current_log_line()
                    if is_traceback:
                        if not (self.line.startswith(" ") or start_traceback):
                            is_traceback = False
        for i, server_log_line in self.gathered_log_lines.items():
            logging.info(f"{server_crawl_log.name} {i}: {server_log_line.strip()}")
        assert 0 == error_count, f"{error_count} errors in {str(server_crawl_log)}"
