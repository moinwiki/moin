"""test_response_codes spider local site and show failures for non-200 responses"""

import csv
import logging
import os
import pytest
from subprocess import run, PIPE, STDOUT
from typing import List

from moin.utils.iri import Iri
from contrib.sitetesting.scrapy.refChecker.spiders.ref_checker import CrawlResult

SITE_SCHEME = 'http'
SITE_HOST = '127.0.0.1:8080'
SITE_URL = Iri(scheme=SITE_SCHEME, authority=SITE_HOST, path='/')
DO_CRAWL = True  # for test development, skip the crawl, load most recent crawl.csv
logger = logging.getLogger(__name__)


class CrawlResults:
    """singleton class to run and cache the results of the crawl"""
    _results: List[CrawlResult] = None

    @classmethod
    def results(cls) -> List[CrawlResult]:
        if cls._results:
            return cls._results
        cwd = os.getcwd()
        try:
            os.chdir(os.path.join(os.path.dirname(__file__), 'scrapy'))
            if DO_CRAWL:
                p = run(['scrapy', 'crawl', '-a', f'url={SITE_URL}', 'ref_checker'], stdout=PIPE, stderr=STDOUT)
                with open('crawl.log', 'wb') as f:
                    f.write(p.stdout)
                assert p.returncode == 0
            with open('crawl.csv') as f:
                in_csv = csv.DictReader(f)
                cls._results = [CrawlResult(**r) for r in in_csv]
            return cls._results

        finally:
            os.chdir(cwd)


@pytest.fixture
def crawl_results():
    return CrawlResults.results()


def test_home_page(crawl_results):
    assert len(crawl_results) > 0
    r = crawl_results[0]
    assert r.url == Iri(scheme=SITE_SCHEME, authority=SITE_HOST, path='/Home'), f'unexpected redirect for / {r}'


def test_200(crawl_results):
    for r in [r for r in crawl_results if r.url.authority == SITE_HOST]:
        if 'Discussion' in r.url.path:
            assert r.response_code in (200, 404), f'{r.response_code} for {r}'
        elif 'MissingSubItem' in r.url.path or 'MissingSubitem' in r.url.path or 'MissingPage' in r.url.path:
            assert r.response_code == 404, f'expected 404, actual {r.response_code} for {r}'
        elif 'WikiMoinMoin' in r.url.path or 'CzymJestMoinMoin' in r.url.path:
            pass  # see test_expected_failures
        else:
            assert r.response_code == 200, f'{r.response_code} for {r}'


@pytest.mark.xfail
def test_expected_failures(crawl_results):
    for r in [r for r in crawl_results if r.url.authority == SITE_HOST]:
        if 'WikiMoinMoin' in r.url.path or 'CzymJestMoinMoin' in r.url.path:
            assert r.response_code == 200, f'{r.response_code} for {r}'


def test_valid_request(crawl_results):
    for r in crawl_results:
        assert r.response_code, f'no response code for {r}'
