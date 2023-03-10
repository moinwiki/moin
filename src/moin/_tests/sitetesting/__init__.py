
from dataclasses import dataclass, fields, field
from typing import List

try:
    from moin._tests.sitetesting import settings
except ImportError:
    from moin._tests.sitetesting import default_settings as settings
from moin.utils.iri import Iri


@dataclass
class CrawlResult:
    url: Iri = ''
    from_url: Iri = ''
    from_text: str = ''
    from_type: str = ''
    from_history: bool = False
    response_code: int = ''
    response_exc: str = ''

    def __post_init__(self):
        if self.url:
            self.url = Iri(self.url)
        if self.from_url:
            self.from_url = Iri(self.from_url)
        if isinstance(self.from_history, str):  # for parsing csv in test_scrapy_crawl
            self.from_history = self.from_history == 'True'
        if self.response_code:
            self.response_code = int(self.response_code)

    def __repr__(self):
        return f'CrawlResult(url="{str(self.url)}", from_url="{str(self.from_url)}", ' +\
               f'from_text={repr(self.from_text)}, ' +\
               f'from_type={repr(self.from_type)}, from_history={self.from_history}, ' +\
               f'response_code={self.response_code}, response_exc="{self.response_exc}")'


@dataclass
class CrawlResultMatch(CrawlResult):
    url_path_components: List[str] = field(default_factory=list)

    def match(self, other: CrawlResult):
        for f in fields(CrawlResult):
            if (my_value := getattr(self, f.name)) and my_value != getattr(other, f.name):
                return False
        if self.url_path_components:
            if other.url.path:
                for url_path_component in self.url_path_components:
                    if url_path_component in other.url.path:
                        return True
            return False
        return True

    @staticmethod
    def _relative_to_absolute(url: Iri):
        if url and not url.scheme:
            url_path = url.path.fullquoted if url.path else ''
            return Iri(scheme=settings.SITE_SCHEME, authority=settings.SITE_HOST,
                       path=f'{settings.SITE_WIKI_ROOT}{url_path}')
        return url

    def __post_init__(self):
        super().__post_init__()
        self.url = self._relative_to_absolute(self.url)
        self.from_url = self._relative_to_absolute(self.from_url)
