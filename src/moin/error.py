# Copyright: 2004-2005 Nir Soffer <nirs@freeshell.org>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin errors / exception classes.
"""

import sys


class Error(Exception):
    """Base class for MoinMoin errors.

    Use this class when you raise errors or create subclasses that
    may be used to display non-ASCII error messages.

    Standard errors work safely only with strings using ASCII or
    Unicode. This class can be used safely with both strings using
    CHARSET and Unicode.

    You can initialize this class with either Unicode or a string using
    CHARSET encoding. On output, the class will convert the string
    to Unicode or the Unicode to string, using CHARSET.

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
        """Return the error message as str."""
        return self.message

    def __getitem__(self, item):
        """Make it possible to access attributes like a dict"""
        return getattr(self, item)


class CompositeError(Error):
    """Base class for exceptions containing another exception.

    Do not use this class directly; use its more specific subclasses.

    Useful for hiding a low-level error inside a high-level user-facing error,
    while keeping the inner error information for debugging.

    Example::

        class InternalError(CompositeError):
            '''Raise for internal errors.'''

        try:
            # code that might fail...
        except HairyLowLevelError:
            raise InternalError("Sorry, an internal error occurred")

    When showing a traceback, both the InternalError traceback and the
    HairyLowLevelError traceback are available.
    """

    def __init__(self, message):
        """Save system exception info before this exception is raised."""
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
    """Base class for fatal errors we can't handle.

    Do not use this class directly; use its more specific subclasses.
    """


class ConfigurationError(FatalError):
    """Raised when a fatal misconfiguration is found."""


class InternalError(FatalError):
    """Raised when an internal fatal error is found."""
