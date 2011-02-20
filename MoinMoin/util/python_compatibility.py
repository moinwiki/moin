"""
    MoinMoin - Support Package

    Stuff for compatibility with older Python versions

    @copyright: 2007 Heinrich Wendel <heinrich.wendel@gmail.com>,
                2009-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

min_req_exc = Exception("Minimum requirement for MoinMoin is Python 2.6.")

raise min_req_exc # no need to import python_compatibility

