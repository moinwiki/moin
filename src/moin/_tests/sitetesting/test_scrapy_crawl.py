"""test_response_codes spider local site and show failures for non-200 responses"""

import logging
import pytest

try:
    from moin._tests.sitetesting import settings
except ImportError:
    from moin._tests.sitetesting import default_settings as settings
from moin._tests.sitetesting import CrawlResultMatch
from moin.utils.iri import Iri

logger = logging.getLogger(__name__)


class TestSiteCrawl:
    EXPECTED_404 = [
        CrawlResultMatch(
            url_path_components=['MissingSubItem', 'MissingSubitem', 'MissingPage', 'MissingItem']),
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
                                 path=f'{settings.SITE_WIKI_ROOT}/users/Home')),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path='/users/Home'),
                         from_url='/html'),
        CrawlResultMatch(url='/users/Home'),
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
        CrawlResultMatch(url='/rst/users/Home', from_url='/rst'),
        CrawlResultMatch(url='/rst/users'),
        # breadcrumb link produced by clicking on /rst/MissingItem
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/rst')),
        CrawlResultMatch(url=Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                                 path=f'{settings.SITE_WIKI_ROOT}/WikiDict')),
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
        failures = []
        for r in [r for r in crawl_results if r.url
                  and r.url.authority == settings.SITE_HOST and not self.is_known_issue(r)]:
            if 'Discussion' in r.url.path:
                expected = {200, 404}
            elif self.is_expected_404(r):
                expected = {404}
            else:
                expected = {200}
            if r.response_code not in expected:
                failures.append(r)
                logger.error(f'expected {expected} got {r.response_code} for {r}')
        assert len(failures) == 0

    @pytest.mark.xfail
    def test_expected_failures(self, crawl_results):
        failures = []
        for r in [r for r in crawl_results if self.is_known_issue(r)]:
            if r.response_code != 200:
                logger.info(f'known issue {r}')
                failures.append(r)
        assert len(failures) == 0

    @pytest.mark.skip
    def test_known_issues_exist(self, crawl_results):
        """enable this test to check for KNOWN_ISSUES which can be removed
        after removing, be sure to confirm by crawling a host with non-blank SITE_WIKI_ROOT
        as some issues only exist when moin is running behind apache"""
        fixed = []
        for m in self.KNOWN_ISSUES:
            seen = False
            my_fixed = []
            my_not_fixed = []
            for r in [r for r in crawl_results if m.match(r)]:
                seen = True
                if r.response_code == 200:
                    my_fixed.append(r)
                else:
                    my_not_fixed.append(r)
            if not my_not_fixed:
                for r in my_fixed:
                    logger.error(f'{r} matching {m} is fixed')
                    fixed.append((m, r))
            if not seen:
                logger.error(f'match {m} not seen')
                fixed.append((m, None))
        assert len(fixed) == 0

    def test_valid_request(self, crawl_results):
        failures = []
        for r in [r for r in crawl_results if not self.is_known_issue(r)]:
            if not r.response_code:
                logger.error(f'no response code for {r}')
                failures.append(r)
        assert len(failures) == 0
