# Copyright: 2008 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:JohannesBerg
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""
MoinMoin - initialize the "logging" system.

WARNING
-------
Logging must be configured VERY early, before the code in log.getLogger
gets executed. Thus, logging is configured either by:

a) an environment variable MOINLOGGINGCONF that contains the path/filename
   of a logging configuration file — this method overrides all following
   methods (except if it can't read or use that configuration, then it
   will use c))
b) an explicit call to moin.log.load_config('logging.conf') —
   you need to do this very early or a) or c) will happen before
c) using a built-in fallback logging configuration

If logging is not yet configured, log.getLogger will do an implicit
configuration call — then a) or c) is done.

Usage (for wiki server admins)
------------------------------
Either use something like this in a shell script:
MOINLOGGINGCONF=/path/to/logging.conf
export MOINLOGGINGCONF

Or, modify your server adapter script (e.g., moin.cgi) to do this::

    from moin import log
    log.load_config('contrib/logging/logfile')  # XXX please fix this path!

You have to fix that path to use a logging configuration matching your
needs (we provide some examples in the path given there; it is relative to
the uncompressed Moin distribution archive — if you use a Moin package,
you may find it under /usr/share/moin/).
It is likely that you also have to edit the sample logging configurations
we provide (e.g., to fix the log file location).

Usage (for developers)
----------------------
If you write code for Moin, do this at the top of your module::

   from moin import log
   logging = log.getLogger(__name__)

This will create a logger with 'moin.your.module' as its name.
The logger can optionally be configured in the logging configuration.
If you don't configure it, some upper-level logger (e.g., the root logger)
will do the logging.
"""

from __future__ import annotations

import logging
import logging.config
import logging.handlers  # needed for handlers defined there being configurable in logging.conf file
import os
import warnings

from io import StringIO

# This is the "last resort" fallback logging configuration for the case
# that load_config() is either not called at all or is called with a non-working
# logging configuration.
# See http://docs.python.org/library/logging.html#configuring-logging
# We just use stderr output by default; if you want anything else,
# you will have to configure logging.
logging_config = """\
[DEFAULT]
# Default log level; to adjust verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
loglevel=INFO

[loggers]
keys=root

[handlers]
keys=stderr,email

[formatters]
keys=default

[logger_root]
level=%(loglevel)s
handlers=stderr,email

[handler_stderr]
class=StreamHandler
level=NOTSET
formatter=default
args=(sys.stderr, )

[handler_email]
class=moin.log.EmailHandler
level=ERROR
formatter=default
args=()

[formatter_default]
format=%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s
datefmt=
class=logging.Formatter
"""

configured = False
fallback_config = False

# use something like this to ignore warnings:
# warnings.filterwarnings('ignore', r'... regex for warning message to ignore ...')


def _log_warning(message, category, filename, lineno, file=None, line=None):
    # for warnings, we just want to use the logging system, not stderr or other files
    msg = f"{filename}:{lineno}: {category.__name__}: {message}"
    logger = getLogger(__name__)
    # Note: the warning will look like coming from here,
    # but msg contains info about where it really comes from
    logger.warning(msg)


def load_config(conf_fname=None):
    """Load logging config from a config file."""
    global configured
    err_msg = None
    conf_fname = os.environ.get("MOINLOGGINGCONF", conf_fname)
    if conf_fname:
        try:
            conf_fname = os.path.abspath(conf_fname)
            # We open the config file here to be able to give a reasonable
            # error message in case of failure (if we give the filename to
            # fileConfig(), it silently ignores unreadable files and gives
            # unhelpful error messages like "No section: 'formatters'"):
            f = open(conf_fname)
            try:
                logging.config.fileConfig(f)
            finally:
                f.close()
            configured = True
            logger = getLogger(__name__)
            logger.debug(f'using logging configuration read from "{conf_fname}"')
            warnings.showwarning = _log_warning
        except Exception as err:  # XXX be more precise
            err_msg = str(err)
    if not configured:
        # load built-in fallback logging config
        with StringIO(logging_config) as f:
            logging.config.fileConfig(f)
        configured = True
        logger = getLogger(__name__)
        if err_msg:
            logger.warning(f'load_config for "{conf_fname}" failed with "{err_msg}".')
        logger.debug("using logging configuration read from built-in fallback in moin.log module!")
        warnings.showwarning = _log_warning

    import moin

    code_path = os.path.dirname(moin.__file__)
    logger.debug(f"Running {moin.project} {moin.version} code from {code_path}")


def getLogger(name: str | None):
    """Wrapper around logging.getLogger, so we can do some more stuff:

    - preprocess the logger name
    - patch log level constants into the logger object, so it can be used
      instead of the logging module
    """
    if not configured:
        load_config()
    logger = logging.getLogger(name)
    for levelnumber, levelname in logging._levelToName.items():
        setattr(logger, levelname, levelnumber)
    return logger


class EmailHandler(logging.Handler):
    """A custom handler class which sends email for each logging event using
    the wiki mail configuration.
    """

    def __init__(self, toaddrs=[], subject=""):
        """Initialize the handler.

        :param toaddrs: address or list of email addresses to send email to
        :param subject: Unicode email subject
        """
        logging.Handler.__init__(self)
        if isinstance(toaddrs, str):
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject
        self.in_email_handler = False

    def emit(self, record):
        """Emit a record.

        Send the record to the specified addresses.
        """
        # The app config is accessible after logging is initialized, so set the
        # arguments and make the decision to send mail or not here.
        from flask import current_app as app

        try:
            email_tracebacks = app.cfg.email_tracebacks
        except (RuntimeError, AttributeError):
            # likely: RuntimeError: working outside of application context
            # if we get that, we can't access the cfg and can't send mail anyway.
            email_tracebacks = False

        if not email_tracebacks:
            return

        if self.in_email_handler:
            return

        self.in_email_handler = True

        try:
            toaddrs = self.toaddrs if self.toaddrs else app.cfg.admin_emails
            log_level = logging.getLevelName(self.level)
            subject = self.subject if self.subject else f"[{app.cfg.sitename}][{log_level}] Log message"
            msg = self.format(record)
            from moin.mail.sendmail import sendmail

            sendmail(subject, msg, to=toaddrs)
        finally:
            self.in_email_handler = False
