# -*- coding: ascii -*-
"""
    MoinMoin - dealing with version numbers

    @copyright: 2011 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

# see MoinMoin/_tests/test_version.py for examples how to use this:

import re

class Version(tuple):
    """
    Version objects store versions like 1.2.3-4.5alpha6 in a structured
    way and support version comparisons and direct version component access.
    1: major version (digits only)
    2: minor version (digits only)
    3: (maintenance) release version (digits only)
    4.5alpha6: optional additional version specification (str)

    You can create a Version instance either by giving the components, like:
        Version(1,2,3,'4.5alpha6')
    or by giving the composite version string, like:
        Version(version="1.2.3-4.5alpha6").

    Version subclasses tuple, so comparisons to tuples should work.
    Also, we inherit all the comparison logic from tuple base class.
    """
    VERSION_RE = re.compile(
        r"""(?P<major>\d+)
            \.
            (?P<minor>\d+)
            \.
            (?P<release>\d+)
            (-
             (?P<additional>.+)
            )?""",
            re.VERBOSE)

    @classmethod
    def parse_version(cls, version):
        match = cls.VERSION_RE.match(version)
        if match is None:
            raise ValueError("Unexpected version string format: %r" % version)
        v = match.groupdict()
        return int(v['major']), int(v['minor']), int(v['release']), str(v['additional'] or '')

    def __new__(cls, major=0, minor=0, release=0, additional='', version=None):
        if version:
            major, minor, release, additional = cls.parse_version(version)
        return tuple.__new__(cls, (major, minor, release, additional))

    # properties for easy access of version components
    major = property(lambda self: self[0])
    minor = property(lambda self: self[1])
    release = property(lambda self: self[2])
    additional = property(lambda self: self[3])

    def __str__(self):
        version_str = "%d.%d.%d" % (self.major, self.minor, self.release)
        if self.additional:
            version_str += "-%s" % self.additional
        return version_str

