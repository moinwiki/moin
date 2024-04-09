"""
    WSGI Middleware for running WSGI apps behind proxies.

    Analyzes HTTP-X-Forwarded-For header and uses the address our outermost
    trusted proxy is seeing as REMOTE_ADDR.

    @copyright: 2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""


class ProxyTrust:
    """
    Middleware that rewrites the remote address according to trusted
    proxies in the forward chain.
    """

    def __init__(self, app, proxies):
        self.app = app
        self.proxies = proxies

    def __call__(self, environ, start_response):
        if "HTTP_X_FORWARDED_FOR" in environ:
            addrs = environ.pop("HTTP_X_FORWARDED_FOR").split(",")
            addrs = [addr.strip() for addr in addrs]
        elif "REMOTE_ADDR" in environ:
            addrs = [environ["REMOTE_ADDR"]]
        else:
            addrs = [None]
        result = [addr for addr in addrs if addr not in self.proxies]
        if result:
            environ["REMOTE_ADDR"] = result[-1]
        elif addrs[-1] is not None:
            environ["REMOTE_ADDR"] = addrs[-1]
        else:
            del environ["REMOTE_ADDR"]
        return self.app(environ, start_response)
