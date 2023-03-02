"""spider.py spider a site and report on 404 errors for href, src, data, and data-href attribs"""

import csv
from dataclasses import dataclass, fields, astuple
from urllib.parse import urlparse

import scrapy
from scrapy import signals

@dataclass
class Result:
  url: str = ''
  from_url: str = ''
  from_text: str = ''
  from_type: str = ''
  response_code: int = None
  response_exc: Exception = None



class RefCheckerSpider(scrapy.Spider):
    """shamelessly stolen from https://www.linode.com/docs/guides/use-scrapy-to-extract-data-from-html-tags/"""
    name = 'ref_checker'

    def __init__(self, url='http://127.0.0.1:8080/', *args, **kwargs):
        super(RefCheckerSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]
        self.results=[]
        self.domain = ''

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(RefCheckerSpider, cls).from_crawler(crawler, *args, **kwargs)
        # Register the spider_closed handler on spider_closed signal
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_closed(self):
        with open('crawl.csv', 'w') as fh:
            outCsv = csv.writer(fh, lineterminator='\n')
            outCsv.writerow([f.name for f in fields(Result)])
            for result in self.results:
                outCsv.writerow(astuple(result))

    def parse(self, response):
        """ Main method that parse downloaded pages. """
        # If first response, update domain (to manage redirect cases)
        if not self.domain:
            parsed_uri = urlparse(response.url)
            self.domain = parsed_uri.netloc

        try:
            my_data = response.meta['my_data']
        except KeyError:
            my_data = {}
        result = Result(response.url, **my_data)
        result.response_code = response.status
        self.results.append(result)

        # Extract domain of current page
        parsed_uri = urlparse(response.url)
        # Parse new links only:
        #   - if current page is not an extra domain
        if parsed_uri.netloc == self.domain and ('Content-Type' not in response.headers or response.headers['Content-Type'] == b'text/html; charset=utf-8'):
            # Get all the <a> tags
            a_selectors = response.xpath("//a")
            # Loop on each tag
            for selector in a_selectors:
                # Extract the link text
                text = selector.xpath('text()').extract_first()
                if isinstance(text, str):
                    text = text.strip().replace('\n','\\n')
                # Extract the link href
                link = selector.xpath('@href').extract_first()
                if link.startswith('javascript:'):
                    continue
                # Create a new Request obj
                my_data = {}
                my_data['from_url'] = response.url;
                my_data['from_text'] = text
                my_data['from_type'] = 'a'
                try:
                    request = response.follow(link, callback=self.parse, errback=self.errback)
                except Exception as e:
                    result = Result(link, **my_data)
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
                    my_data = {}
                    my_data['from_url'] = response.url;
                    my_data['from_type'] = attrib
                    try:
                        request = response.follow(link, callback=self.parse, errback=self.errback)
                    except Exception as e:
                        result = Result(link, **my_data)
                        result.response_exc = f'unable to create request from {link}: {repr(e)}'
                        self.results.append(result)
                        continue
                    request.meta['my_data'] = my_data
                    yield request

    def errback(self, failure):
        request = failure.request
        try:
            my_data = request.meta['my_data']
        except KeyError:
            my_data = {}
        result = Result(request.url, **my_data)
        try:
            response = failure.value.response
        except AttributeError:
            pass
        else:
            result.response_code = response.status
        result.response_exc = repr(failure)
        self.results.append(result)


