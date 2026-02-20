# Copyright: 2025 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import NamedTuple

from flask import current_app as app
from moin.constants.keys import FIELDS, ITEMID, NAME, NAME_EXACT, NAMESPACE
from moin.storage.types import MetaData


class CompositeName(NamedTuple):
    """
    Named tuple to hold the composite name.
    """

    namespace: str
    field: str
    value: str

    @property
    def split(self):
        """
        Return a dict of field names/values.
        """
        return {NAMESPACE: self.namespace, "field": self.field, "item_name": self.value}

    @property
    def fullname(self):
        return get_fqname(self.value, self.field, self.namespace)

    def __str__(self):
        return self.fullname

    @property
    def query(self):
        """
        Return a dict that can be used as a Whoosh query
        to look up index documents matching this CompositeName.
        """
        field = NAME_EXACT if not self.field else self.field
        return {NAMESPACE: self.namespace, field: self.value}

    def get_root_fqname(self):
        """
        Determine the root item of the namespace of this composite name and return it as new CompositeName instance.
        """
        return CompositeName(self.namespace, NAME_EXACT, app.cfg.root_mapping.get(self.namespace, app.cfg.default_root))


def get_fqname(item_name: str, field: str, namespace: str) -> str:
    """
    Compute a composite name from item_name, field, and namespace.
    Composite name == [NAMESPACE/][@FIELD/]NAME
    """
    if field and field != NAME_EXACT:
        item_name = f"@{field}/{item_name}"
    if namespace:
        item_name = f"{namespace}/{item_name}"
    return item_name


def gen_fqnames(meta: MetaData) -> list[CompositeName]:
    """
    Generate fqnames from metadata.
    """
    if meta[NAME]:
        return [CompositeName(meta[NAMESPACE], NAME_EXACT, name) for name in meta[NAME]]
    return [CompositeName(meta[NAMESPACE], ITEMID, meta[ITEMID])]


def parent_names(names: list[str]) -> set[str]:
    """
    Compute list of parent names (same order as in names, but no dupes)

    :param names: item NAME from whoosh index, where NAME is a list
    :return: parent names list
    """
    parents = set()
    for name in names:
        parent_tail = name.rsplit("/", 1)
        if len(parent_tail) == 2:
            parents.add(parent_tail[0])
    return parents


def split_namespace(namespaces: list[str] | set[str], url: str) -> tuple[str, str]:
    """
    Find the longest namespace in the set.
    Namespaces are separated by slashes (/).
    Example:
        namespaces: ['ns1', 'ns1/ns2']
        url: ns1/urlalasd -> ns1, urlalasd
        url: ns3/urlalasd -> '', ns3/urlalasd
        url: ns2/urlalasd -> '', ns2/urlalasd
        url: ns1/ns2/urlalasd -> ns1/ns2, urlalasd
    :param namespaces: set of namespaces (strings) to search
    :param url: string
    :return: (namespace, url)
    """
    namespace = ""
    tokens_list = url.split("/")
    for token in tokens_list:
        if namespace:
            token = f"{namespace}/{token}"
        if token in namespaces:
            namespace = token
        else:
            break
    if namespace:
        length = len(namespace) + 1
        url = url[length:]
    return namespace, url


def split_fqname(url: str) -> CompositeName:
    """
    Split a fully qualified URL into namespace, field, and page name.
    URL -> [NAMESPACE/][@FIELD/]NAME

    :param url: the URL to split
    :returns: a namedtuple CompositeName(namespace, field, item_name)
    Examples::

        url: 'ns1/ns2/@itemid/Page' return 'ns1/ns2', 'itemid', 'Page'
        url: '@revid/OtherPage' return '', 'revid', 'OtherPage'
        url: 'ns1/Page' return 'ns1', '', 'Page'
        url: 'ns1/ns2/@notfield' return 'ns1/ns2', '', '@notfield'
    """
    if not url:
        return CompositeName("", NAME_EXACT, "")
    namespaces = {namespace.rstrip("/") for namespace, _ in app.cfg.namespace_mapping}
    namespace, url = split_namespace(namespaces, url)
    field = NAME_EXACT
    if url.startswith("@"):
        tokens = url[1:].split("/", 1)
        if tokens[0] in FIELDS:
            field = tokens[0]
            url = tokens[1] if len(tokens) > 1 else ""
    return CompositeName(namespace, field, url)
