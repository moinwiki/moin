# Copyright: 2026 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import Any, Final, TYPE_CHECKING

import secrets

from dataclasses import dataclass
from flask import request, url_for, Response
from moin.error import ConfigurationError

if TYPE_CHECKING:
    from flask import Response
    from flask.wrappers import Request
    from moin.config import WikiConfigProtocol

NONCE_ATTR = "csp_nonce"

NONCE_LENGTH = 32


@dataclass
class CspProfile:
    rules: str
    rules_report_only: str
    report_endpoints: dict[str, str]
    report_uri: str


@dataclass
class CspConfiguration:
    use_nonces: bool
    profiles: dict[str, CspProfile]


class CspConfigCreator:

    valid_rules: Final = (
        "base-uri",
        "child-src",
        "connect-src",
        "default-src",
        "font-src",
        "form-action",
        "frame-ancestors",
        "frame-src",
        "img-src",
        "media-src",
        "report-to",
        "report-uri",
        "require-trusted-types-for",
        "script-src",
        "script-src-attr",
        "script-src-elem",
        "style-src",
        "style-src-attr",
        "style-src-elem",
        "trusted-types",
        "object-src",
        "upgrade-insecure-requests",
        "worker-src",
    )

    @classmethod
    def read_rules(cls, rules_dict: dict[str, str | list[str]]) -> str:
        if not rules_dict:
            return ""
        rules: list[str] = []
        for name, value in rules_dict.items():
            if name not in cls.valid_rules:
                raise ConfigurationError(f"Invalid CSP rule: {name}")
            if isinstance(value, list):
                value = " ".join(value)
            value = value.replace("@self", "'self'")
            rules.append(f"{ name } { value }")
        return "; ".join(rules)

    @classmethod
    def read_profiles(cls, profiles_dict: dict[str, Any]) -> dict[str, CspProfile]:
        if not profiles_dict:
            return {}
        profiles: dict[str, CspProfile] = {}
        for name, profile_dict in profiles_dict.items():
            rules = cls.read_rules(profile_dict.get("rules"))
            rules_report_only = cls.read_rules(profile_dict.get("rules-report-only"))
            report_endpoints = profile_dict.get("report-endpoints", {})
            report_uri = profile_dict.get("report-uri", "")
            if report_uri == "@default":
                report_uri = url_for("frontend.cspreport")
            profiles[name] = CspProfile(
                rules=rules,
                rules_report_only=rules_report_only,
                report_endpoints=report_endpoints,
                report_uri=report_uri,
            )
        return profiles

    @classmethod
    def create(cls, wiki_config) -> CspConfiguration:
        profiles = cls.read_profiles(wiki_config.csp_profiles)
        return CspConfiguration(use_nonces=True, profiles=profiles)


csp_config: CspConfiguration | None = None


def configure_csp(config: WikiConfigProtocol):
    global csp_config
    csp_config = CspConfigCreator.create(config)


def make_csp_nonce() -> str:
    """
    Returns a random nonce.
    """
    return secrets.token_urlsafe(NONCE_LENGTH)


def get_csp_nonce() -> str:
    return getattr(request, NONCE_ATTR, "")


def set_csp_nonce(request: Request) -> None:
    if not getattr(request, NONCE_ATTR, None):
        setattr(request, NONCE_ATTR, make_csp_nonce())


def set_csp_headers(response, profile, nonce):

    def append_directive(policy, directive):
        return f"{policy}; {directive}" if policy else directive

    # enforcing policy
    if policy_value := profile.rules:
        if nonce:
            policy_value = policy_value.replace("{NONCE}", nonce)
        if profile.report_uri:
            policy_value = append_directive(policy_value, f"report-uri { url_for('frontend.cspreport') }")
        response.headers["Content-Security-Policy"] = policy_value

    # report only policy
    if policy_value := profile.rules_report_only:
        if nonce:
            policy_value = policy_value.replace("{NONCE}", nonce)
        for endpoint_name in profile.report_endpoints:
            policy_value = append_directive(policy_value, f"report-to {endpoint_name}")
        if profile.report_uri:
            policy_value = append_directive(policy_value, f"report-uri { url_for('frontend.cspreport') }")
        response.headers["Content-Security-Policy-Report-Only"] = policy_value

    # reporting endpoints
    if profile.report_endpoints:
        endpoints_header_value = " ".join([f'{name}="{uri}"' for name, uri in profile.report_endpoints.items()])
        response.headers["Reporting-Endpoints"] = endpoints_header_value


def add_csp_headers(response: Response) -> Response:
    """
    Add Content-Security-Policy headers to the HTTP response.
    """
    assert csp_config
    profile = csp_config.profiles.get("default")
    nonce_value = get_csp_nonce() if csp_config.use_nonces else None
    set_csp_headers(response, profile, nonce_value)
    return response
