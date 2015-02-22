#!/usr/bin/env python
# Copyright: 2001 by Juergen Hermann <jh@web.de>
# Copyright: 2001-2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import os
import MoinMoin  # validate python version


basedir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(basedir, 'README.txt')) as f:
    long_description = f.read()

from setuptools import setup, find_packages


setup_args = dict(
    name="moin",
    version=str(MoinMoin.version),
    description="MoinMoin is an easy to use, full-featured and extensible wiki software package",
    long_description=long_description,
    author="Juergen Hermann et al.",
    author_email="moin-user@lists.sourceforge.net",
    # maintainer(_email) not active because distutils/register can't handle author and maintainer at once
    download_url='http://static.moinmo.in/files/moin-%s.tar.gz' % (MoinMoin.version, ),
    url="http://moinmo.in/",
    license="GNU GPL v2 (or any later version)",
    keywords="wiki web",
    platforms="any",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
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
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business :: Groupware",
        "Topic :: Text Processing :: Markup",
    ],

    packages=find_packages(exclude=['_tests', ]),

    # package_dir={'MoinMoin.translations': 'MoinMoin/translations',
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
        # 'https://github.com/mitsuhiko/werkzeug/tarball/master#egg=Werkzeug-0.9.2-dev',
        # 'https://github.com/mitsuhiko/flask/tarball/master#egg=Flask-0.11-dev',
        # 'https://bitbucket.org/thomaswaldmann/whoosh/get/default.tar.gz#egg=Whoosh-2.5.99dev',
        # use a pre-release and fixed flask-themes 0.2.0 as 0.1.3 does not work for flask 0.8.x:
        'https://bitbucket.org/thomaswaldmann/flask-themes/get/a87399231886.tar.gz#egg=Flask-Themes-0.2.0',
        # use a pre-release emeraldtree (port to 2.6/2.7/3.3):
        'https://bitbucket.org/thomaswaldmann/emeraldtree/get/tip.tar.gz#egg=emeraldtree-0.9.3dev',
        'https://bitbucket.org/thomaswaldmann/flatland-fixes/get/bb7ecc64bf96.tar.gz#egg=flatland-0.0.3',
    ],
    install_requires=[
        'blinker>=1.1',  # event signalling (e.g. for change notification trigger)
        'docutils>=0.8.1',  # reST markup processing
        'Markdown>=2.1.1',  # Markdown markup processing
        'Flask>=0.10',  # micro framework
        'Flask-Babel>=0.7',  # i18n support
        'Flask-Cache>=0.3.4',  # caching support
        'Flask-Script==1.0.0',  # scripting support
        'Flask-Themes>=0.2.0',  # theme support
        'emeraldtree>=0.9.3dev',  # xml processing
        'flatland',  # form handling
        'Jinja2>=2.7',  # template engine
        'pygments>=1.4',  # src code / text file highlighting
        'Werkzeug==0.9.6',  # wsgi toolkit
        'pytest<2.7',  # pytest is needed by unit tests (only tested with 2.5 and 2.6)
        'pytest-pep8<1.1',  # coding style checker (only tested with 1.0.x)
        'whoosh>=2.5.0',  # needed for indexed search
        'sphinx>=1.1',  # needed to build the docs
        'pdfminer==20110515',  # pdf -> text/plain conversion, XXX 20131113 fails see #385
        'passlib>=1.6.0',  # strong password hashing (1.6 needed for consteq)
        'XStatic>=0.0.2',  # support for static file pypi packages
        'XStatic-Bootstrap==3.1.1.2',
        'XStatic-Font-Awesome>=4.1.0.0',
        'XStatic-CKEditor>=3.6.1.2',
        'XStatic-autosize',
        'XStatic-jQuery>=1.8.2',
        'XStatic-jQuery-File-Upload==4.4.2',  # newer version not tested yet
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
            ('MoinMoin/templates/dictionary.js', 'javascript', None),  # all JS translatable strings must be defined here for jQuery i18n plugin
            ('MoinMoin/apps/**/templates/**.html', 'jinja2', None),
            ('MoinMoin/themes/**/templates/**.html', 'jinja2', None),
            ('MoinMoin/**/_tests/**', 'ignore', None),
            ('MoinMoin/static/**', 'ignore', None),
            ('MoinMoin/**.py', 'python', None),
        ],
    },

)

if __name__ == '__main__':
    setup(**setup_args)
