# Copyright: 2004-2005 Nir Soffer <nirs@freeshell.org>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin errors / exception classes
"""

import sys


class Error(Exception):
    """Base class for moin moin errors

    Use this class when you raise errors or create sub classes that
    may be used to display non ASCII error message.

    Standard errors work safely only with strings using ascii or
    unicode. This class can be used safely with both strings using
    CHARSET and unicode.

    You can init this class with either unicode or string using
    CHARSET encoding. On output, the class will convert the string
    to unicode or the unicode to string, using CHARSET.

    When you want to render an error, use unicode() or str() as needed.
    """

    def __init__(self, message):
        """Initialize an error, decode if needed

        :param message: str, bytes or object that supports __str__.
        """
        if isinstance(message, bytes):
            message = message.decode()
        if not isinstance(message, str):
            message = str(message)
        self.message = message

    def __str__(self):
        """Return str error message"""
        return self.message

    def __getitem__(self, item):
        """Make it possible to access attributes like a dict"""
        return getattr(self, item)


class CompositeError(Error):
    """Base class for exceptions containing an exception

    Do not use this class but its more specific sub classes.

    Useful for hiding low level error inside high level user error,
    while keeping the inner error information for debugging.

    Example::

        class InternalError(CompositeError):
            ''' Raise for internal errors '''

        try:
            # code that might fail...
        except HairyLowLevelError:
            raise InternalError("Sorry, internal error occurred")

    When showing a traceback, both InternalError traceback and
    HairyLowLevelError traceback are available.
    """

    def __init__(self, message):
        """Save system exception info before this exception is raised"""
        Error.__init__(self, message)
        self.innerException = sys.exc_info()

    def exceptions(self):
        """Return a list of all inner exceptions"""
        all = [self.innerException]
        while True:
            lastException = all[-1][1]
            try:
                all.append(lastException.innerException)
            except AttributeError:
                break
        return all


class FatalError(CompositeError):
    """Base class for fatal error we can't handle

    Do not use this class but its more specific sub classes.
    """


class ConfigurationError(FatalError):
    """Raise when fatal misconfiguration is found"""


class InternalError(FatalError):
    """Raise when internal fatal error is found"""
