"""ref_checker.py spider a site and report on 404 errors for href, src, data, and data-href attribs"""

import csv
from dataclasses import fields, astuple
import logging

import scrapy
from scrapy import signals
from scrapy.exceptions import IgnoreRequest

from moin._tests.sitetesting import CrawlResult

try:
    from moin._tests.sitetesting import settings
except ImportError:
    from moin._tests.sitetesting import default_settings as settings

from moin.utils.iri import Iri

logger = logging.getLogger(__name__)


class RefCheckerSpider(scrapy.Spider):
    """shamelessly stolen from https://www.linode.com/docs/guides/use-scrapy-to-extract-data-from-html-tags/"""
    name = 'ref_checker'

    def __init__(self, url='http://127.0.0.1:8080/', do_history=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [url]
        if isinstance(do_history, str):
            do_history = do_history.lower() == 'true'
        self.do_history = do_history
        self.no_crawl_paths = ['/MoinWikiMacros/MonthCalendar']  # lots of 404s for the dates
        self.results = []
        self.domain = ''

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        # Register the spider_closed handler on spider_closed signal
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_closed(self):
        with open('crawl.csv', 'w') as fh:
            out_csv = csv.writer(fh, lineterminator='\n')
            out_csv.writerow([f.name for f in fields(CrawlResult)])
            for result in self.results:
                out_csv.writerow(astuple(result))

    def parse(self, response, **kwargs):
        """ Main method that parse downloaded pages. """
        # If first response, update domain (to manage redirect cases)
        if not self.domain:
            parsed_uri = Iri(response.url)
            self.domain = parsed_uri.authority
        try:
            result = response.meta['my_data']
        except KeyError:
            result = CrawlResult(response.url)
        result.response_code = response.status
        self.results.append(result)
        is_history = result.from_history
        # Parse new links
        #   - if current page is not an extra domain
        #   - if none of self.no_crawl_paths is in the url_path
        #   - skip +history pages if not self.do_history
        #   - for moin pages require html content type
        #   - for dump-html pages follow when there is no content type
        #   - if CRAWL_NAMESPACE is defined do not follow links outside the NAMESPACE
        follow = True
        parsed_uri = Iri(response.url)
        result.url = parsed_uri  # in case of redirect show final url in crawl.csv
        if (url_path := parsed_uri.path) and '+history' in url_path:
            is_history = True
        if is_history and not self.do_history:
            follow = False
        if parsed_uri.path:
            url_path_str = parsed_uri.path.fullquoted
            for no_crawl_path in self.no_crawl_paths:
                if no_crawl_path in url_path_str:
                    follow = False
                    logging.info(f'not crawling {response.url}')
                    break
            if (settings.CRAWL_NAMESPACE
                    and not url_path_str.startswith(f'{settings.SITE_WIKI_ROOT}{settings.CRAWL_NAMESPACE}')):
                logger.info(f'not crawling {url_path_str}')
                follow = False
        if (follow and parsed_uri.authority == self.domain
                and ('Content-Type' not in response.headers
                     or response.headers['Content-Type'] == b'text/html; charset=utf-8')):
            for attrib in ['href', 'data-href', 'src', 'data']:
                attrib_selectors = response.xpath(f'//*[@{attrib}]')
                for selector in attrib_selectors:
                    link = selector.xpath(f'@{attrib}').extract_first()
                    text = selector.xpath('text()').extract_first()
                    if isinstance(text, str):
                        text = text.strip().replace('\n', '\\n')
                    new_result = CrawlResult(link, response.url, text, attrib, is_history)
                    if new_result.url.scheme in {'javascript', 'file'}:
                        continue
                    try:
                        request = response.follow(link, callback=self.parse, errback=self.errback)
                        new_result.url = Iri(request.url)  # response.follow handles relative links
                    except Exception as e:
                        new_result.response_exc = f'unable to create request from {link}: {repr(e)}'
                        self.results.append(new_result)
                        continue
                    request.meta['my_data'] = new_result
                    yield request

    def errback(self, failure):
        if failure.value.__class__ is IgnoreRequest:
            return
        request = failure.request
        try:
            result = request.meta['my_data']
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
