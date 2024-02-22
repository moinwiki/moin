#!/usr/bin/env python
# Copyright: 2001 by Juergen Hermann <jh@web.de>
# Copyright: 2001-2024 MoinMoin:ThomasWaldmann
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from setuptools import setup


setup_args = dict(
    # stuff for babel:
    message_extractors={
        'src': [
            ('moin/templates/**.html', 'jinja2', None),
            ('moin/templates/dictionary.js', 'jinja2', None),  # all JS translatable strings must be
                                                               # defined here for jQuery i18n plugin
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
