#!/usr/bin/env python
# Copyright: 2001 by Juergen Hermann <jh@web.de>
# Copyright: 2001-2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import sys
import os

from MoinMoin import project, version

if sys.hexversion < 0x2060000:
    # we require 2.6.x or 2.7.x, python 3.x does not work yet.
    sys.stderr.write("%s %s requires Python 2.6 or greater.\n" % (project, str(version)))
    sys.exit(1)

with open('README.txt') as f:
    long_description = f.read()

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
    #             'MoinMoin.themes.foobar': 'MoinMoin/themes/foobar',
    #             'MoinMoin.templates': 'MoinMoin/templates',
    #             'MoinMoin.apps.admin.templates': 'MoinMoin/apps/admin/templates',
    #             'MoinMoin.apps.misc.templates': 'MoinMoin/apps/misc/templates',
    #            },

    package_data={
        'MoinMoin.translations': ['MoinMoin.pot', '*.po', ],
        'MoinMoin.static': ['*', ],
        'MoinMoin.themes.modernized': ['*', ],
        'MoinMoin.themes.foobar': ['*', ],
        'MoinMoin.templates': ['*.html', '*.xml', ],
        'MoinMoin.apps.admin.templates': ['*.html', ],
        'MoinMoin.apps.misc.templates': ['*.html', '*.txt', ],
    },
    include_package_data=True,
    zip_safe=False,
    dependency_links=[
        # 'https://github.com/mitsuhiko/werkzeug/tarball/master#egg=Werkzeug-0.7dev',
        'https://bitbucket.org/thomaswaldmann/whoosh/get/2.4x.tar.gz#egg=Whoosh-2.4.99dev',
        # fixed flask-themes, 0.1.3 does not work for flask 0.8.x, thus we use a faked 0.1.3.1:
        'https://bitbucket.org/thomaswaldmann/flask-themes/get/24dcc703953f.tar.gz#egg=Flask-Themes-0.1.3.1',
        'https://bitbucket.org/thomaswaldmann/emeraldtree/get/tip.tar.gz#egg=emeraldtree-0.9.2',
    ],
    install_requires=[
        'blinker>=1.1',  # event signalling (e.g. for change notification trigger)
        'docutils>=0.8.1',  # reST markup processing
        'Markdown>=2.1.1',  # Markdown markup processing
        'Flask>=0.8',  # micro framework
        'Flask-Babel>=0.7',  # i18n support
        'Flask-Cache>=0.3.4',  # caching support
        'Flask-Script>=0.3.3',  # scripting support
        'Flask-Themes>=0.1.3.1',  # theme support
        'emeraldtree>=0.9.2',  # xml processing
        'flatland==dev',  # repo checkout at revision 269:6c5d262d7eff works
        'Jinja2>=2.6',  # template engine
        'pygments>=1.4',  # src code / text file highlighting
        'Werkzeug>=0.8.1',  # wsgi toolkit
        'pytest>=2.1, <2.3',  # pytest is needed by unit tests
                              # note: currently 2.3.x is not compatible with our test code,
                              # likely due to the fixtures changes.
        'pytest-pep8<1.0.3',  # coding style checker
                              # note: pytest-pep8 1.0.3 needs pytest 2.3
        'whoosh>=2.4.0',  # needed for indexed search
        'sphinx>=1.1',  # needed to build the docs
        'pdfminer',  # pdf -> text/plain conversion
        'passlib>=1.6.0',  # strong password hashing (1.6 needed for consteq)
        'XStatic>=0.0.2',  # support for static file pypi packages
        'XStatic-CKEditor>=3.6.1.2',
        'XStatic-jQuery>=1.8.2',
        'XStatic-jQuery-File-Upload>=4.4.2',
        'XStatic-JSON-js',
        'XStatic-svgweb>=2011.2.3.2',
        'XStatic-TWikiDraw-moin>=2004.10.23.2',
        'XStatic-AnyWikiDraw>=0.14.2',
        'XStatic-svg-edit-moin>=2012.11.15.1',
    ],
    # optional features and their list of requirements
    extras_require={
        #'featurename': ["req1", "req2", ],
        'pil': ["PIL"],  # used by image get for scaling/rotating/etc.
                         # PIL is a binary dependency and some features of it
                         # require special libs/header to be installed before
                         # it can be compiled successfully
        'ldap': ["python-ldap>=2.0.0"],  # used by ldap auth
        'openid': ["python-openid>=2.2.4"],  # used by openid rp auth
        'sqla': ["sqlalchemy>=0.7.1"],  # used by sqla store
        'mongodb': ["pymongo"],  # used by mongodb store
    },
    entry_points=dict(
        console_scripts=['moin = MoinMoin.script:main'],
    ),

    # stuff for babel:
    message_extractors={
        '': [
            ('MoinMoin/templates/**.html', 'jinja2', None),
            ('MoinMoin/templates/**.js', 'javascript', None),
            ('MoinMoin/apps/**/templates/**.html', 'jinja2', None),
            ('MoinMoin/apps/**/templates/**.js', 'javascript', None),
            ('MoinMoin/**/_tests/**', 'ignore', None),
            ('MoinMoin/static/**', 'ignore', None),
            ('MoinMoin/**.py', 'python', None),
        ],
    },

)

if __name__ == '__main__':
    setup(**setup_args)
