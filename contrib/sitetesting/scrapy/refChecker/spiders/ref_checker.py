"""ref_checker.py spider a site and report on 404 errors for href, src, data, and data-href attribs"""

import csv
from dataclasses import dataclass, fields, astuple
import logging

import scrapy
from scrapy import signals
from scrapy.exceptions import IgnoreRequest

from moin.utils.iri import Iri

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    url: Iri
    from_url: Iri = ''
    from_text: str = ''
    from_type: str = ''
    from_history: bool = False
    response_code: int = ''
    response_exc: str = ''

    def __post_init__(self):
        self.url = Iri(self.url)
        if self.from_url:
            self.from_url = Iri(self.from_url)
        self.from_history = self.from_history == 'True'
        if self.response_code:
            self.response_code = int(self.response_code)

    def __repr__(self):
        return f'CrawlResult(url={str(self.url)}, from_url="{str(self.from_url)}", ' +\
               f'from_text={repr(self.from_text)}, ' +\
               f'from_type={repr(self.from_type)}, from_history={self.from_history}, ' +\
               f'response_code={self.response_code}, response_exc="{self.response_exc}")'


class RefCheckerSpider(scrapy.Spider):
    """shamelessly stolen from https://www.linode.com/docs/guides/use-scrapy-to-extract-data-from-html-tags/"""
    name = 'ref_checker'

    def __init__(self, url='http://127.0.0.1:8080/', do_history=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [url]
        if isinstance(do_history, str):
            do_history = do_history.lower() == 'true'
        self.no_crawl_paths = ['/MoinWikiMacros/MonthCalendar']  # lots of 404s for the dates
        if not do_history:
            self.no_crawl_paths.append('/+history/')
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
        if '/+history/' in response.url:
            is_history = True
        # Extract domain of current page
        parsed_uri = Iri(response.url)
        # Parse new links only:
        #   - if current page is not an extra domain
        #   - for moin pages require html content type
        #   - for dump-html pages follow when there is no content type
        follow = True
        if parsed_uri.path:
            url_path = parsed_uri.path.fullquoted
            for no_crawl_path in self.no_crawl_paths:
                if no_crawl_path in url_path:
                    follow = False
                    logging.info(f'not crawling {response.url}')
                    break
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
                    result = CrawlResult(link, response.url, text, attrib, is_history)
                    if result.url.scheme in {'javascript', 'file'}:
                        continue
                    try:
                        request = response.follow(link, callback=self.parse, errback=self.errback)
                        result.url = Iri(request.url)
                    except Exception as e:
                        result.response_exc = f'unable to create request from {link}: {repr(e)}'
                        self.results.append(result)
                        continue
                    request.meta['my_data'] = result
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
