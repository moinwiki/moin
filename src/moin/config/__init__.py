# Copyright: 2011-2013 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable, TypeAlias, TypedDict, TYPE_CHECKING
from collections.abc import Callable

from moin.datastructures.backends import BaseDictsBackend, BaseGroupsBackend

if TYPE_CHECKING:
    from moin.auth import BaseAuth
    from moin.storage.backends import BackendBase

NamespaceMapping: TypeAlias = list[tuple[str, str]]

BackendMapping: TypeAlias = dict[str, "BackendBase"]

ItemViews: TypeAlias = list[tuple[str, str, str, bool]]

NaviBarEntries: TypeAlias = list[tuple[str, str, dict[str, Any], str, str]]


class AclConfig(TypedDict):
    before: str
    default: str
    after: str
    hierarchic: bool


AclMapping: TypeAlias = list[tuple[str, AclConfig]]

IndexStorageConfig: TypeAlias = tuple[str, tuple[str, Any], dict]


class PasswordHasherConfig(TypedDict):
    time_cost: int
    memory_cost: int
    parallelism: int
    hash_len: int
    salt_len: int


@runtime_checkable
class WikiConfigProtocol(Protocol):
    acl_functions: str
    acl_mapping: AclMapping
    acl_rights_contents: list[str]
    acl_rights_functions: list[str]
    acls: dict[str, AclConfig]
    admin_emails: list[str]
    auth: list[BaseAuth]
    auth_can_logout: list[str]
    auth_login_inputs: list[str]
    auth_have_login: bool
    backend_mapping: BackendMapping
    backends: dict[str, str]
    config_check_enabled: bool
    content_dir: str
    content_security_policy: str
    content_security_policy_report_only: str
    content_security_policy_limit_per_day: int
    contenttype_disabled: list[str]
    contenttype_enabled: list[str]
    data_dir: str
    default_root: str
    destroy_backend: bool
    dicts: Callable[[], BaseDictsBackend]
    edit_locking_policy: str
    edit_lock_time: int
    email_tracebacks: bool
    endpoints_excluded: list[str]
    expanded_quicklinks_size: int
    groups: Callable[[], BaseGroupsBackend]
    index_storage: IndexStorageConfig
    instance_dir: str
    interwikiname: str
    interwiki_map: dict[str, str]
    item_views: ItemViews
    language_default: str
    locale_default: str
    mail_enabled: bool
    mail_from: str | None
    mail_username: str | None
    mail_password: str | None
    mail_sendmail: str | None
    mail_smarthost: str | None
    markdown_extensions: list[str] = []
    mimetypes_to_index_as_empty: list[str] = []
    namespace_mapping: NamespaceMapping
    namespaces: dict[str, str]
    navi_bar: NaviBarEntries
    registration_hint: str
    registration_only_by_superuser: bool
    root_mapping: dict[str, str]
    secrets: dict[str, str] | str
    serve_files: dict[str, str]
    show_hosts: bool
    siteid: str
    sitename: str
    supplementation_item_names: list[str]
    template_dirs: list[str]
    theme_default: str
    timezone_default: str
    uri: str
    user_defaults: dict[str, Any]
    user_email_unique: bool
    user_email_verification: bool
    user_gravatar_default_img: str
    user_homewiki: str
    user_use_gravatar: bool
    wikiconfig_dir: str

    _plugin_modules: list[str]
    _site_plugin_lists: dict[str, dict[str, str]]
