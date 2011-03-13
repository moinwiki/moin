#!/usr/bin/env python
# Copyright: 2001 by Juergen Hermann <jh@web.de>
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import sys, os

from MoinMoin import version

if sys.hexversion < 0x2060000:
    # we require 2.6.x or 2.7.x, python 3.x does not work yet.
    sys.stderr.write("%s %s requires Python 2.6 or greater.\n" % (project, str(version)))
    sys.exit(1)

long_description = open('README.txt').read()

from setuptools import setup, find_packages


setup_args = dict(
    name="moin",
    version=str(version),
    description="MoinMoin is an easy to use, full-featured and extensible wiki software package",
    long_description=long_description,
    author="Juergen Hermann et al.",
    author_email="moin-user@lists.sourceforge.net",
    # maintainer(_email) not active because distutils/register can't handle author and maintainer at once
    download_url='http://static.moinmo.in/files/moin-%s.tar.gz' % (version, ),
    url="http://moinmo.in/",
    license="GNU GPL v2 (or any later version)",
    keywords="wiki web",
    platforms="any",
    classifiers="""\
Development Status :: 2 - Pre-Alpha
Environment :: Web Environment
Intended Audience :: Education
Intended Audience :: End Users/Desktop
Intended Audience :: Information Technology
Intended Audience :: Other Audience
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Topic :: Internet :: WWW/HTTP :: WSGI
Topic :: Internet :: WWW/HTTP :: WSGI :: Application
Topic :: Internet :: WWW/HTTP :: Dynamic Content
Topic :: Office/Business :: Groupware
Topic :: Text Processing :: Markup""".splitlines(),

    packages=find_packages(exclude=['_tests', ]),

    #package_dir={'MoinMoin.translations': 'MoinMoin/translations',
    #             'MoinMoin.static': 'MoinMoin/static',
    #             'MoinMoin.themes.modernized': 'MoinMoin/themes/modernized',
    #             'MoinMoin.templates': 'MoinMoin/templates',
    #             'MoinMoin.apps.admin.templates': 'MoinMoin/apps/admin/templates',
    #             'MoinMoin.apps.misc.templates': 'MoinMoin/apps/misc/templates',
    #            },

    package_data={'MoinMoin.translations': ['MoinMoin.pot', '*.po', ],
                  'MoinMoin.static': ['*', ],
                  'MoinMoin.themes.modernized': ['*', ],
                  'MoinMoin.templates': ['*.html', '*.xml', ],
                  'MoinMoin.apps.admin.templates': ['*.html', ],
                  'MoinMoin.apps.misc.templates': ['*.html', '*.txt', ],
                 },
    zip_safe=False,
    dependency_links = [
        # hack needed as install from pypi fails for Werkzeug==dev due to
        # wrong dev URL in the long description.
        'https://github.com/mitsuhiko/werkzeug/tarball/master#egg=Werkzeug-0.7dev',
    ],
    install_requires=[
        'blinker>=1.1', # event signalling (e.g. for change notification trigger)
        'docutils>=0.6', # reST markup processing
        'Flask>=0.6', # micro framework
        'Flask-Babel>=0.6', # i18n support
        'Flask-Cache>=0.3.2', # caching support
        'Flask-Script>=0.3', # scripting support
        'Flask-Themes>=0.1', # theme support
        'emeraldtree>=0.9.0', # xml processing
        'flatland==dev', # repo checkout at revision 269:6c5d262d7eff works
        'Jinja2>=2.5', # template engine
        'pygments>=1.1.1', # src code / text file highlighting
        'sqlalchemy>=0.6.0', # metadata index and other stuff
        #'Werkzeug>=0.7dev', # wsgi toolkit, dev version (do not use ==0.7dev!)
        'Werkzeug==0.6.2', # use this if 0.7dev fails
        'py==1.3.4', # py.test 1.3.4 is needed by unit tests
        'sphinx', # needed to build the docs
    ],
    # optional features and their list of requirements
    extras_require = {
        #'featurename': ["req1", "req2", ],
        'pil': ["PIL"], # used by image get for scaling/rotating/etc.
                        # PIL is a binary dependency and some features of it
                        # require special libs/header to be installed before
                        # it can be compiled successfully
        'ldap': ["python-ldap>=2.0.0"], # used by ldap auth
        'openid': ["python-openid>=2.2.4"], # used by openid rp auth
        'hg': ["mercurial"], # used by mercurial backend
    },
    entry_points = dict(
        console_scripts = ['moin = MoinMoin.script:main'], # TODO
    ),

    # stuff for babel:
    message_extractors = {
        '': [
            ('MoinMoin/templates/**.html', 'jinja2', None),
            ('MoinMoin/apps/**/templates/**.html', 'jinja2', None),
            ('MoinMoin/**/_tests/**', 'ignore', None),
            ('MoinMoin/script/old/**', 'ignore', None),
            ('MoinMoin/filter/EXIF.py', 'ignore', None),
            ('MoinMoin/static/**', 'ignore', None),
            ('MoinMoin/**.py', 'python', None),
        ],
    },

)

if __name__ == '__main__':
    setup(**setup_args)

