"""ref_checker.py spider a site and report on 404 errors for href, src, data, and data-href attribs"""

import csv
from dataclasses import dataclass, fields
from enum import Enum
import logging
from urllib.parse import urlparse

import scrapy
from scrapy import signals
from scrapy.exceptions import IgnoreRequest

from moin.utils.iri import Iri

logger = logging.getLogger(__name__)


class FromType(Enum):
    A = 'a'
    DATA_HREF = 'data-href'
    SRC = 'src'
    DATA = 'data'


@dataclass
class CrawlResult:
    url: Iri
    from_url: Iri = ''
    from_text: str = ''
    from_type: FromType = ''
    from_history: bool = False
    response_code: int = ''
    response_exc: str = ''

    def __post_init__(self):
        self.url = Iri(self.url)
        if self.from_url:
            self.from_url = Iri(self.from_url)
        if self.from_type:
            self.from_type = FromType(self.from_type)
        self.from_history = self.from_history == 'True'
        if self.response_code:
            self.response_code = int(self.response_code)

    def __repr__(self):
        return f'CrawlResult(url={str(self.url)}, from_url="{str(self.from_url)}", ' +\
               f'from_text={repr(self.from_text)}, ' +\
               f'from_type="{self.from_type.value}", from_history={self.from_history}, ' +\
               f'response_code={self.response_code}, response_exc="{self.response_exc}"'

    def as_csv_row(self):
        row = (getattr(self, field.name) for field in fields(self))
        row = (t.value if isinstance(t, Enum) else str(t) for t in row)
        return row


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
                out_csv.writerow(result.as_csv_row())

    def parse(self, response, **kwargs):
        """ Main method that parse downloaded pages. """
        # If first response, update domain (to manage redirect cases)
        if not self.domain:
            parsed_uri = urlparse(response.url)
            self.domain = parsed_uri.netloc

        try:
            my_data = response.meta['my_data']
        except KeyError:
            my_data = {}
        result = CrawlResult(response.url, **my_data)
        result.response_code = response.status
        self.results.append(result)
        is_history = my_data.get('from_history', False)
        if '/+history/' in response.url:
            is_history = True

        # Extract domain of current page
        parsed_uri = urlparse(response.url)
        # Parse new links only:
        #   - if current page is not an extra domain
        #   - for moin pages require html content type
        #   - for dump-html pages follow when there is no content type
        follow = True
        for no_crawl_path in self.no_crawl_paths:
            if no_crawl_path in parsed_uri.path:
                follow = False
                logging.info(f'not crawling {response.url}')
                break
        if (follow and parsed_uri.netloc == self.domain
            and ('Content-Type' not in response.headers
                 or response.headers['Content-Type'] == b'text/html; charset=utf-8')):
            # Get all the <a> tags exclude breadcrumbs as the from_url on breadcrumbs can be misleading
            a_selectors = response.xpath("//a[not(../../ul[contains(@class,'moin-breadcrumb')])]")
            # Loop on each tag
            for selector in a_selectors:
                # Extract the link text
                text = selector.xpath('text()').extract_first()
                if isinstance(text, str):
                    text = text.strip().replace('\n', '\\n')
                # Extract the link href
                link = selector.xpath('@href').extract_first()
                if link.startswith('javascript:'):
                    continue
                # Create a new Request obj
                my_data = {'from_url': response.url, 'from_text': text, 'from_type': 'a', 'from_history': is_history}
                try:
                    request = response.follow(link, callback=self.parse, errback=self.errback)
                except Exception as e:
                    result = CrawlResult(link, **my_data)
                    result.response_exc = f'unable to create request from {link}: {repr(e)}'
                    self.results.append(result)
                    continue
                request.meta['my_data'] = my_data
                # Return it thanks to a generator
                yield request
            for attrib in ['data-href', 'src', 'data']:
                attrib_selectors = response.xpath(f'//*[@{attrib}]')
                for selector in attrib_selectors:
                    link = selector.xpath(f'@{attrib}').extract_first()
                    my_data = {'from_url': response.url, 'from_type': attrib}
                    try:
                        request = response.follow(link, callback=self.parse, errback=self.errback)
                    except Exception as e:
                        result = CrawlResult(link, **my_data)
                        result.response_exc = f'unable to create request from {link}: {repr(e)}'
                        self.results.append(result)
                        continue
                    request.meta['my_data'] = my_data
                    yield request

    def errback(self, failure):
        if failure.value.__class__ is IgnoreRequest:
            return
        request = failure.request
        try:
            my_data = request.meta['my_data']
        except KeyError:
            my_data = {}
        result = CrawlResult(request.url, **my_data)
        try:
            response = failure.value.response
        except AttributeError:
            pass
        else:
            result.response_code = response.status
        result.response_exc = repr(failure)
        self.results.append(result)
