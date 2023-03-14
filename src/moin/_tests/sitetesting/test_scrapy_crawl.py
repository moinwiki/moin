"""test_response_codes spider local site and show failures for non-200 responses"""

import csv
import logging
from subprocess import Popen
import os
import pytest
from signal import SIGINT
from subprocess import run, PIPE, STDOUT
import sys
from time import sleep
from typing import List

try:
    from moin._tests.sitetesting import settings
except ImportError:
    from moin._tests.sitetesting import default_settings as settings
from moin._tests.sitetesting import CrawlResult, CrawlResultMatch
from moin._tests import check_connection
from moin.utils.iri import Iri

logger = logging.getLogger(__name__)


class CrawlResults:
    """singleton class to run and cache the results of the crawl"""
    _results: List[CrawlResult] = None

    @classmethod
    def results(cls) -> List[CrawlResult]:
        if cls._results is not None:
            return cls._results
        cwd = os.getcwd()
        my_dir = os.path.dirname(__file__)
        scrapy_dir = os.path.join(my_dir, 'scrapy')
        server = None
        os.chdir(scrapy_dir)
        started = False
        try:
            if settings.DO_CRAWL:
                cls._results = []  # prevent attempting crawl after failed attempt
                if settings.SITE_HOST == '127.0.0.1:9080':
                    os.chdir(my_dir)
                    server = Popen(['python', './run_moin.py'], stdout=PIPE, stderr=STDOUT)
                    wait_count = 0
                    while not started and wait_count < 6:
                        wait_count += 1
                        sleep(5)
                        try:
                            check_connection(9080)
                        except Exception as e:
                            logger.info(f'waiting for server startup {e}')
                        else:
                            started = True
                    if not started:
                        raise RuntimeError('moin not started')
                    os.chdir(scrapy_dir)
                com = ['scrapy', 'crawl', '-a', f'url={settings.CRAWL_START}', 'ref_checker']
                p = run(com, stdout=PIPE, stderr=STDOUT)
                with open('crawl.log', 'wb') as f:
                    f.write(p.stdout)
                assert p.returncode == 0, f'command {com} failed.  log:\n{p.stdout.decode()}'
            with open('crawl.csv') as f:
                in_csv = csv.DictReader(f)
                cls._results = [CrawlResult(**r) for r in in_csv]
            return cls._results
        finally:
            if server:
                server.send_signal(SIGINT)
                os.chdir(my_dir)
                with open('server.log', 'wb') as f:
                    out, _ = server.communicate()
                    f.write(out)
                if not started:
                    logger.error('server not started. log:')
                    logger.error(out.decode())
            os.chdir(cwd)


@pytest.fixture
def crawl_results():
    return CrawlResults.results()


@pytest.mark.skipif(sys.platform == "win32" and 'GITHUB_RUN_NUMBER' in os.environ,
                    reason="too slow for github windows build host")
class TestSiteCrawl:
    EXPECTED_404 = [
        CrawlResultMatch(
            url_path_components=['MissingSubItem', 'MissingSubitem', 'MissingPage', 'MissingItem', 'users']),
    ]
    KNOWN_ISSUES = [
        # CrawlResultMatch(url_path_components=['WikiMoinMoin', 'CzymJestMoinMoin']),  # only on sample
        CrawlResultMatch(
            url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST, path=f'{settings.SITE_WIKI_ROOT}/html'),
            from_url='/markdown'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/Sibling'),
                         from_url='/markdown'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/markdown', fragment='unsupported-html-tags'),
                         from_url='/markdown'),
        CrawlResultMatch(url='/markdown/Home', from_url='/markdown'),
        CrawlResultMatch(
            url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST, path='/+get/help-common/logo.png'),
            from_url='/markdown'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/MoinWikiMacros/MonthCalendar'),
                         from_url='/MoinWikiMacros'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/MoinWikiMacros/Icons'),
                         from_url='/MoinWikiMacros'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/WikiDict'),
                         from_url='/MoinWikiMacros'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/MoinWikiMacros', fragment='anchorname'),
                         from_url='/MoinWikiMacros'),
        CrawlResultMatch(url='/StronaGłówna', from_url='/MoinWikiMacros'),
        CrawlResultMatch(url='/rst/Home', from_url='/rst'),
        CrawlResultMatch(url='http://localhost:8080/+serve/ckeditor/plugins/smiley/images/shades_smile.gif',
                         from_url='/html'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST, path='/Home'),
                         from_url='/html'),
        # CrawlResultMatch(url='http://127.0.0.1:8080/Home', from_url='/html'),  # only on sample
        CrawlResultMatch(url='http://localhost:8080/Home', from_url='/html'),
        CrawlResultMatch(url='http://127.0.0.1:8080/users/Home', from_url='/html'),
        # CrawlResultMatch(url="http://zip", from_url="/MoinWikiMacros", from_type='data-href'),  # only on sample
        CrawlResultMatch(url="/creole/subitem", from_url="/creole"),
        # CrawlResultMatch(url="http://fontawesome.io/icons/"),  # intermittent DNS lookup error
        CrawlResultMatch(
            url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST, path=f'{settings.SITE_WIKI_ROOT}/Home')),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/+get/audio.mp3'),
                         from_url='/mediawiki'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/+get/video.mp4'),
                         from_url='/mediawiki'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/+get/svg'),
                         from_url='/mediawiki'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/+get/png'),
                         from_url='/mediawiki'),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/+get/jpeg'),
                         from_url='/mediawiki'),
    ]

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
        assert len(crawl_results) > 0
        r = crawl_results[0]
        expected = CrawlResultMatch(url='/Home')
        assert expected.match(r), f'unexpected redirect for / {r}'

    def test_200(self, crawl_results):
        for r in [r for r in crawl_results if r.url.authority == settings.SITE_HOST and not self.is_known_issue(r)]:
            if 'Discussion' in r.url.path:
                assert r.response_code in (200, 404), f'{r.response_code} for {r}'
            elif self.is_expected_404(r):
                assert r.response_code == 404, f'expected 404, actual {r.response_code} for {r}'
            else:
                assert r.response_code == 200, f'{r.response_code} for {r}'

    @pytest.mark.xfail
    def test_expected_failures(self, crawl_results):
        for r in [r for r in crawl_results if self.is_known_issue(r)]:
            assert r.response_code == 200, f'{r.response_code} for {r}'

    @pytest.mark.skip
    def test_known_issues_exist(self, crawl_results):
        """enable this test to check for KNOWN_ISSUES which can be removed
        after removing, be sure to confirm by crawling a host with non-blank SITE_WIKI_ROOT
        as some issues only exist when moin is running behind apache"""
        fixed = []
        for m in self.KNOWN_ISSUES:
            seen = False
            for r in [r for r in crawl_results if m.match(r)]:
                seen = True
                if r.response_code == 200:
                    fixed.append((m, r))
                    logger.error(f'{r} matching {m} is fixed')
            if not seen:
                logger.error(f'match {m} not seen')
                fixed.append((m, None))
        assert len(fixed) == 0, f'{len(fixed)} known issues have been fixed'

    def test_valid_request(self, crawl_results):
        for r in [r for r in crawl_results if not self.is_known_issue(r)]:
            assert r.response_code, f'no response code for {r}'
