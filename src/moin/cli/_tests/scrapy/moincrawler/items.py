# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - dataclasses for items gathered during the crawl tests.

Scrapy item docs: https://docs.scrapy.org/en/latest/topics/items.html
"""

from dataclasses import dataclass, fields, field

from moin.utils.iri import Iri

try:
    from moin.cli._tests import settings
except ImportError:
    from moin.cli._tests import default_settings as settings


@dataclass
class CrawlResult:
    """Represent the result of a GET in the crawl, written to crawl.csv when the spider closes."""

    url: Iri = ""
    from_url: Iri = ""
    from_text: str = ""  # link text, if any
    from_type: str = ""  # attribute name where this link was found
    response_code: int = ""
    response_exc: str = ""  # exception, if any

    def __post_init__(self):
        if self.url:
            self.url = Iri(self.url)
        if self.from_url:
            self.from_url = Iri(self.from_url)
        if self.response_code:
            self.response_code = int(self.response_code)

    def __str__(self):
        return (
            f'url="{str(self.url)}", from_url="{str(self.from_url)}", '
            + f"from_text={repr(self.from_text)}, "
            + f"from_type={repr(self.from_type)}, "
            + f'response_code={self.response_code}, response_exc="{self.response_exc}"'
        )

    def __repr__(self):
        return f"CrawlResult({str(self)})"


@dataclass
class CrawlResultMatch(CrawlResult):
    """Class for matching against CrawlResult.

    If initialized with a relative URL, prepend CRAWL_START for matching,
    e.g., '/html' -> 'http://127.0.0.1:9080/help-en/html'.
    """

    url_path_components: list[str] = field(default_factory=list)  # list of path components to match against

    def match(self, other: CrawlResult) -> bool:
        """Return True if:

        - For each of my non-None fields, the other object has the exact same value.
        - If url_path_components is set, require at least one of them to appear in other.url.path.
        """
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
        """Prepend CRAWL_START to a relative URL."""
        if url and not url.scheme:
            url_path = url.path.fullquoted if url.path else ""
            return Iri(
                scheme=settings.SITE_SCHEME,
                authority=settings.SITE_HOST,
                path=f"{settings.SITE_WIKI_ROOT}{settings.CRAWL_NAMESPACE}{url_path}",
            )
        return url

    def __post_init__(self):
        super().__post_init__()
        self.url = self._relative_to_absolute(self.url)
        self.from_url = self._relative_to_absolute(self.from_url)

    def __str__(self):
        return super().__str__() + f" url_path_components={repr(self.url_path_components)}"

    def __repr__(self):
        return f"CrawlResultMatch({str(self)})"
