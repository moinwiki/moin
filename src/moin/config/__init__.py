# Copyright: 2011-2013 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import Any, Protocol, TypedDict

type NamespaceMapping = list[tuple[str, str]]

type BackendMapping = dict[str, Any]

type AclMapping = list[tuple[str, AclConfig]]

type ItemViews = list[tuple[str, str, str, bool]]

type NaviBarEntries = list[tuple[str, str, dict[str, Any], str, str]]


class AclConfig(TypedDict):
    before: str
    default: str
    after: str
    hierarchic: bool


class WikiConfigProtocol(Protocol):
    wikiconfig_dir: str
    instance_dir: str
    data_dir: str
    index_storage: str
    serve_files: dict[str, str]
    template_dirs: list[str]
    interwikiname: str
    interwiki_map: dict[str, str]
    sitename: str
    edit_locking_policy: str
    edit_lock_time: int
    expanded_quicklinks_size: int
    admin_emails: list[str]
    email_tracebacks: bool
    registration_only_by_superuser: bool
    registration_hint: str
    user_email_verification: bool
    acl_functions: str
    uri: str
    namespaces: dict[str, str]
    backends: dict[str, str]
    acls: dict[str, AclConfig]
    namespace_mapping: NamespaceMapping
    backend_mapping: BackendMapping
    acl_mapping: AclMapping
    root_mapping: dict[str, str]
    default_root: str
    language_default: str
    content_dir: str
    endpoints_excluded: list[str]
    item_views: ItemViews
    supplementation_item_names: list[str]
    navi_bar: NaviBarEntries
    auth_login_inputs: list[str]
    auth_have_login: bool
    show_hosts: bool
    user_homewiki: str
