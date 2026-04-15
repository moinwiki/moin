# Copyright: 2026 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from typing import TYPE_CHECKING

import secrets

from flask import request, url_for, Response
from moin import current_app

if TYPE_CHECKING:
    from flask.wrappers import Request
    from flask import Response

NONCE_ATTR = "csp_nonce"

NONCE_LENGTH = 32


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


def add_csp_headers(response: Response) -> Response:
    """
    Add Content-Security-Policy headers to the HTTP response.
    """

    cfg = current_app.cfg

    if cfg.content_security_policy:
        response.headers["Content-Security-Policy"] = cfg.content_security_policy

    if cfg.content_security_policy_report_only:
        nonce_value = get_csp_nonce()
        # report only policy
        policy_value = cfg.content_security_policy_report_only
        policy_value = policy_value.replace("{NONCE}", nonce_value)
        policy_value = f"{policy_value} report-uri { url_for('frontend.cspreport') };"
        response.headers["Content-Security-Policy-Report-Only"] = policy_value

    return response
