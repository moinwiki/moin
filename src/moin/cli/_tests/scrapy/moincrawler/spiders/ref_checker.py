# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli._tests.scrapy.moincrawler.ref_checker

spider a moin site and report on 404 and other errors for href, src, data, and data-href attribs
this spider is run via moin.cli._tests.conftest.do_crawl via moin.cli._tests.test_scrapy_crawl
"""

import csv
from dataclasses import fields, astuple
import os
from traceback import print_exc

import scrapy
from scrapy import signals
from scrapy.exceptions import IgnoreRequest

from moin._tests import get_dirs
from moin.cli._tests.scrapy.moincrawler.items import CrawlResult

try:
    from moin.cli._tests import settings
except ImportError:
    from moin.cli._tests import default_settings as settings

from moin.cli._tests.conftest import get_crawl_csv_path
from moin.utils.iri import Iri
from moin import log

logging = log.getLogger(__name__)


class RefCheckerSpider(scrapy.Spider):
    """crawl moin pages following href, src, data, and data-href attributes

    this spider is run via moin.cli._tests.conftest.do_crawl via moin.cli._tests.test_scrapy_crawl
    on close the spider writes results to _test_artifacts/crawl.csv
    crawl.csv will be read by test_scrapy_crawl
    original design shamelessly stolen (with permission) from
        https://www.linode.com/docs/guides/use-scrapy-to-extract-data-from-html-tags/"""

    name = "ref_checker"

    def __init__(self, url="http://127.0.0.1:8080/", *args, **kwargs):
        """:param url: start url for crawl, overridden by settings.CRAWL_START in moin.cli.conftest.do_crawl"""
        super().__init__(*args, **kwargs)
        self.start_urls = [url]
        self.no_crawl_paths = ["/MoinWikiMacros/MonthCalendar"]  # lots of 404s for the dates
        self.results = []
        self.domain = ""

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        # Register the spider_closed handler on spider_closed signal
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_closed(self):
        logging.info("entering spider_closed")
        try:
            _, artifact_base_dir = get_dirs("")
            for k, c in self.crawler.stats.get_stats().items():  # bubble up spider exceptions into test failures
                if k.startswith("spider_exceptions"):
                    logging.error(f"spider_exception: {c}")
                    self.results.append(CrawlResult(response_exc=f"crawler stats: {k} = {c}"))
            crawl_csv_path = os.environ.get("MOIN_SCRAPY_CRAWL_CSV", get_crawl_csv_path())
            logging.info(f"writing {len(self.results)} to {crawl_csv_path}")
            with open(crawl_csv_path, "w") as fh:
                out_csv = csv.writer(fh, lineterminator="\n")
                out_csv.writerow([f.name for f in fields(CrawlResult)])
                for result in self.results:
                    out_csv.writerow(astuple(result))
        except Exception as e:  # noqa
            logging.error(f"exception in spider_closed {repr(e)}")
            print_exc()
            raise

    def _parse(self, response, **kwargs):
        """Main method that parses downloaded pages.

        requests yielded from this method are added to the crawl queue"""
        try:
            result = response.meta["my_data"]
        except KeyError:
            result = CrawlResult(response.url)
        result.response_code = response.status
        self.results.append(result)
        # Do not follow links on current page if
        #   - if url_path is blank
        #   - for moin pages require text/html Content-Type
        #   - for dump-html pages follow when there is no Content-Type
        #   - if current page url is not in matching domain as CRAWL_START
        #   - if +history is in the url_path
        #   - if any of self.no_crawl_paths is in the url_path
        #   - if CRAWL_NAMESPACE is defined and url_path is outside the NAMESPACE
        follow = True
        parsed_uri = Iri(response.url)
        result.url = parsed_uri  # in case of redirect show final url in crawl.csv
        if not (url_path := parsed_uri.path):
            logging.debug(f"not crawling blank path {response.url}")
            follow = False
        if "Content-Type" in response.headers and response.headers["Content-Type"] != b"text/html; charset=utf-8":
            logging.debug(f'not crawling Content-Type {response.headers["Content-Type"]} {response.url}')
            follow = False
        # If first response, update domain (to manage redirect cases)
        if not self.domain:
            self.domain = parsed_uri.authority
        if parsed_uri.authority != self.domain:
            logging.debug(f"not crawling external link {response.url}")
            follow = False
        if follow and parsed_uri.path:
            if "+history" in url_path:
                logging.debug(f"not crawling history {response.url}")
                follow = False
            url_path_str = parsed_uri.path.fullquoted
            for no_crawl_path in self.no_crawl_paths:
                if no_crawl_path in url_path_str:
                    follow = False
                    logging.debug(f"not crawling no_crawl_path {response.url}")
                    break
            if settings.CRAWL_NAMESPACE and not url_path_str.startswith(
                f"{settings.SITE_WIKI_ROOT}{settings.CRAWL_NAMESPACE}"
            ):
                logging.debug(f'not crawling outside of CRAWL_NAMESPACE "{settings.CRAWL_NAMESPACE}" {url_path_str}')
                follow = False
        if follow:
            for attrib in ["href", "data-href", "src", "data"]:
                attrib_selectors = response.xpath(f"//*[@{attrib}]")
                for selector in attrib_selectors:
                    link = selector.xpath(f"@{attrib}").extract_first()
                    text = selector.xpath("text()").extract_first()
                    if isinstance(text, str):
                        text = text.strip().replace("\n", "\\n")
                    new_result = CrawlResult(link, response.url, text, attrib)
                    if new_result.url.scheme in {"javascript", "file", "mailto"}:
                        continue
                    try:
                        request = response.follow(link, callback=self.parse, errback=self.errback)
                        new_result.url = Iri(request.url)  # response.follow handles relative links
                    except Exception as e:
                        # for badly formed href, append to results with response_exc
                        # so issue will be shown in test failures
                        # but do not yield as we cannot follow this link
                        new_result.response_exc = f"unable to create request from {link}: {repr(e)}"
                        self.results.append(new_result)
                        continue
                    request.meta["my_data"] = new_result
                    yield request

    def parse(self, response, **kwargs):
        """called by scrapy framework"""
        try:
            yield from self._parse(response, **kwargs)
        except Exception as e:  # noqa
            logging.error(f"parse exception : {repr(e)}")
            print_exc()
            raise

    def errback(self, failure):
        """called when request comes back with anything other than a 200 OK response"""
        if failure.value.__class__ is IgnoreRequest:  # ignore urls disallowed by robots.txt
            return
        request = failure.request
        try:
            result = request.meta["my_data"]
        except KeyError:
            result = CrawlResult(request.url)
        try:
            response = failure.value.response
        except AttributeError:
            pass
        else:
            result.response_code = response.status
        result.response_exc = repr(failure)
        self.results.append(result)
