# Copyright: 2026 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

from flask import url_for, Response

from moin import current_app


def add_csp_headers(response: Response) -> Response:
    """
    Add Content-Security-Policy headers to the HTTP response.
    """

    cfg = current_app.cfg

    if cfg.content_security_policy:
        response.headers["Content-Security-Policy"] = cfg.content_security_policy

    if cfg.content_security_policy_report_only:
        response.headers["Content-Security-Policy-Report-Only"] = (
            f"{cfg.content_security_policy_report_only} report-uri {url_for('frontend.cspreport')}; "
        )

    return response
