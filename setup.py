#!/usr/bin/env python
# Copyright: 2001 by Juergen Hermann <jh@web.de>
# Copyright: 2001-2018 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import os
import platform
import sys
from setuptools import setup, find_packages


if sys.hexversion < 0x3050000:
    sys.exit("Error: MoinMoin requires Python 3.5+., current version is %s\n" % (platform.python_version(), ))


basedir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(basedir, 'README.rst')) as f:
    long_description = f.read()


setup_args = dict(
    name="moin",
    description="MoinMoin is an easy to use, full-featured and extensible wiki software package",
    long_description_content_type="text/x-rst",
    long_description=long_description,
    author="Juergen Hermann et al.",
    author_email="moin-user@python.org",
    # maintainer(_email) not active because distutils/register can't handle author and maintainer at once
    url="https://moinmo.in/",
    license="GNU GPL v2 (or any later version)",
    keywords="wiki web",
    platforms="any",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Other Audience",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business :: Groupware",
        "Topic :: Text Processing :: Markup",
    ],

    packages=find_packages(where='src', exclude=['_tests', ]),
    package_dir={'': 'src'},

    package_data={
        'moin.translations': ['MoinMoin.pot', '*.po', ],
        'moin.static': ['*', ],
        'moin.themes.modernized': ['*', ],
        'moin.themes.basic': ['*', ],
        'moin.themes.topside': ['*', ],
        'moin.themes.topside_cms': ['*', ],
        'moin.templates': ['*.html', '*.xml', ],
        'moin.apps.admin.templates': ['*.html', ],
        'moin.apps.misc.templates': ['*.html', '*.txt', ],
    },
    include_package_data=True,
    zip_safe=False,
    use_scm_version={
        'write_to': os.path.join(basedir, 'src', 'moin', '_version.py'),
    },
    setup_requires=[
        'setuptools_scm',  # magically cares for version and packaged files
    ],
    install_requires=[
        'blinker>=1.1',  # event signalling (e.g. for change notification trigger)
        'docutils>=0.8.1',  # reST markup processing
        'Markdown>=3.0.0',  # Markdown markup processing
        'Flask<2.0.0',  # micro framework
        'Flask-Babel>=0.11.1',  # i18n support
        'Flask-Caching>=1.2.0',  # caching support
        'Flask-Script>=2.0.5',  # scripting support
        'Flask-Theme>=0.3.5',  # theme support
        'emeraldtree>=0.10.0',  # xml processing
        'feedgen==0.9.*',  # Atom feed
        'flatland>=0.8',  # form handling
        'Jinja2<3.0.0',  # template engine
        'pygments>=1.4',  # src code / text file highlighting
        'Werkzeug<2.0.0',  # wsgi toolkit
        'whoosh>=2.7.0',  # needed for indexed search
        'pdfminer3',  # pdf -> text/plain conversion
        'passlib>=1.6.0',  # strong password hashing (1.6 needed for consteq)
        'sqlalchemy>=1.3.16',  # used by sqla store TODO see: #1014
        'XStatic>=0.0.2',  # support for static file pypi packages
        'XStatic-Bootstrap==3.1.1.2',
        'XStatic-Font-Awesome>=4.1.0.0',
        'XStatic-CKEditor>=3.6.1.2',
        'XStatic-autosize',
        'XStatic-jQuery>=1.8.2',
        'XStatic-jQuery-File-Upload>=10.31.0',
        'XStatic-TWikiDraw-moin>=2004.10.23.2',
        'XStatic-AnyWikiDraw>=0.14.2',
        'XStatic-svg-edit-moin>=2012.11.15.1',
        'XStatic-JQuery.TableSorter>=2.14.5.1',
        'XStatic-Pygments>=1.6.0.1',
    ],
    # optional features and their list of requirements
    extras_require={
        # 'featurename': ["req1", "req2", ],
        'pillow': ["pillow"],  # successor to PIL; used by image get for scaling/rotating/etc.;
                               # requires special libs/header to be installed before it can be compiled successfully
        'ldap': ["python-ldap>=2.0.0"],  # used by ldap auth
                                         # requires special libs/header to be installed before it can be compiled successfully
                                         # windows binaries available from 3rd parties
        # 'sqla': ["sqlalchemy>=0.7.1"],  # used by sqla store
    },
    entry_points=dict(
        console_scripts=['moin = moin.scripts:main'],
    ),

    # stuff for babel:
    message_extractors={
        'src': [
            ('moin/templates/**.html', 'jinja2', None),
            ('moin/templates/dictionary.js', 'javascript', None),  # all JS translatable strings must be defined here for jQuery i18n plugin
            ('moin/apps/**/templates/**.html', 'jinja2', None),
            ('moin/themes/**/templates/**.html', 'jinja2', None),
            ('moin/**/_tests/**', 'ignore', None),
            ('moin/static/**', 'ignore', None),
            ('moin/**.py', 'python', None),
        ],
    },
)


if __name__ == '__main__':
    setup(**setup_args)
