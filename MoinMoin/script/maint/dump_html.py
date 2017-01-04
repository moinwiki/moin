# Copyright: 2015-2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Creates a static dump of HTML files for each current item in this wiki.

Usage (activate the virtual environment):
    moin dump-html --theme=topside_cms --directory=HTML

    where:
        --directory specifies output location, defaults to HTML
        --theme specifies theme, defaults to wikiconfig theme_default value

Works best with a CMS-like theme that suppresses the wiki navigation links for login, edit,
etc. that are not useful within a static HTML dump.

The html files created will not have names ending with .html, just as the paths used by the wiki
server do not end with .html (e.g. http://127.0.0.1/Home)

For convenience, copies of the starting page and index page are created with
names ending with .html. All browsers tested follow links to pages
not having .html suffixes without complaint.

TODO:
    * add feature to accept userid and password options (in case items are protected with ACLs)
    * add feature to limit output to selected pages
    * fix issues related to missing or misleading filename suffixes. Using data from contrib/sample/:
        * all browsers think the audio.mp3 and video.mp4 html files are corrupt, a .html suffix is needed
            * actual media files are in the +get sub-directory
        * all browsers fail to display the svg image file, a .svg suffix is needed on the /+get/svg file
"""

import sys
import os
import shutil
import re

from flask import current_app as app
from flask_script import Command, Option

from whoosh.query import Every

from werkzeug.exceptions import Forbidden

from xstatic.main import XStatic

from MoinMoin.app import create_app
from MoinMoin.apps.frontend.views import show_item
from MoinMoin.app import before_wiki
from MoinMoin.constants.keys import CURRENT, THEME_NAME

from wikiconfig import Config

from MoinMoin import log
logging = log.getLogger(__name__)

SLASH = '(2f)'


class Dump(Command):
    description = 'Create a static HTML image of this wiki.'

    option_list = [
        Option('--directory', '-d', dest='directory', type=unicode, required=False, default='HTML',
               help='Directory name containing the output files.'),
        Option('-t', '--theme', dest='theme', required=False, default=None,
               help='Name of theme to be used in creating output pages'),
    ]

    def run(self, directory='HTML', theme=None):
        if theme:
            app.cfg.user_defaults[THEME_NAME] = theme
        before_wiki()
        html_root = os.path.dirname(os.path.abspath(__file__)) + '/../../../{0}/'.format(directory)
        repo_root = os.path.dirname(os.path.abspath(__file__)) + '/../../../'
        moin_root = os.path.dirname(os.path.abspath(__file__)) + '/../../'
        # make an empty output directory
        if os.path.exists(html_root):
            shutil.rmtree(html_root, ignore_errors=False)
        else:
            os.makedirs(html_root)
        # create subdirectories and copy static css, icons, images
        get_dir = html_root + '/+get'  # images and other raw data from wiki content
        os.makedirs(get_dir)
        shutil.copytree(moin_root + '/static', html_root + 'static')
        shutil.copytree(repo_root + '/wiki_local', html_root + '+serve/wiki_local')
        # copy files from xstatic packaging
        pkg = Config.pkg
        # TODO: add option to not load bootstrap; is autosize wanted?
        for dirs in ['font_awesome', 'jquery', 'bootstrap', 'autosize', 'jquery_tablesorter', ]:
            xs = XStatic(getattr(pkg, dirs), root_url='/static', provider='local', protocol='http')
            shutil.copytree(xs.base_dir, html_root + '+serve/%s' % dirs)

        # copy directories for theme's static files
        theme = app.cfg.user_defaults[THEME_NAME]
        if theme == 'topside_cms':
            # topside_cms uses topside CSS files
            from_dir = moin_root + '/themes/topside/static'
        else:
            from_dir = moin_root + '/themes/%s/static' % theme
        to_dir = html_root + '_themes/%s' % theme
        shutil.copytree(from_dir, to_dir)

        # convert: <img alt="svg" src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg" />
        # to:      <img alt="svg" src="+get/svg" />
        invalid_src = re.compile(r' src="/\+get/\+[0-9a-f]{32}/')
        valid_src = u' src="+get/'

        names = []
        for current_rev in app.storage.search(Every(), limit=None):
            # ignore all user items
            if current_rev.namespace == 'userprofiles':
                continue

            # remove / characters from sub-item filenames
            file_name = current_rev.name.replace('/', SLASH)
            filename = html_root + file_name

            try:
                rendered = show_item(current_rev.name, CURRENT)
                names.append(file_name)  # build index containing items successfully rendered
            except Forbidden:  # Forbidden
                print 'Failed to dump %s: Forbidden' % current_rev.name
                continue

            # make hrefs relative to current folder
            rendered = rendered.replace('href="/', 'href="')
            rendered = rendered.replace('src="/static/', 'src="static/')
            rendered = rendered.replace('src="/+serve/', 'src="+serve/')
            rendered = rendered.replace('href="+index/"', 'href="+index"')  # trailing slash changes relative position
            rendered = rendered.replace('<a href="">', '<a href="%s">' % app.cfg.default_root)  # TODO: fix basic theme
            # remove item ID from: src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg"
            rendered = re.sub(invalid_src, valid_src, rendered)
            rendered = self.subitems(rendered)

            with open(filename, 'wb') as f:
                f.write(rendered.encode('utf8'))
            if current_rev.name == app.cfg.default_root:
                # for convenience, duplicates of home page are easy to find in directory list and open with a click
                for target in ['index.html', '_index.html', current_rev.name + '.html']:
                    with open(html_root + target, 'wb') as f:
                        f.write(rendered.encode('utf8'))
                sample_page = rendered  # save a copy for creation of index page
            # copy raw data for all items to output; images are required, text items are of marginal benefit
            item = app.storage[current_rev.name]
            rev = item[CURRENT]
            with open(get_dir + '/' + file_name, 'wb') as df:
                shutil.copyfileobj(rev.data, df)

        # work around differences is basic and modernized theme layout
        # TODO: this is likely to break as new themes are added
        if theme == 'basic':
            start = '<div id="moin-content" lang="en" dir="ltr">'  # basic
            end = '<div class="navbar moin-footer">'
        else:
            start = '<div id="moin-content">'  # modernized , cms
            end = '<div id="moin-footer">'
        div_end = '</div></div>'
        # build a page named "+index" containing links to all wiki items
        ul = '<h1>Index</h1><ul>%s</ul>'
        li = '<li><a href="%s">%s</a></li>'
        links = []
        names.sort()
        for name in names:
            links.append(li % (name, name.replace(SLASH, '/')))
        name_links = ul % ('\n'.join(links))
        part1 = sample_page.split(start)[0]
        part2 = sample_page.split(end)[1]
        page = part1 + start + name_links + div_end + end + part2
        for target in ['+index', '+index.html']:
            with open(html_root + target, 'wb') as f:
                f.write(page.encode('utf8'))

    def subitems(self, s, target='href="'):
        """
        fix links to subitems
          * <a href="Home/subitem"> becomes <a href="Home(2f)subitem">
          * do not change  href="https://moinmo.in/FrontPage"
          * do not change href="+serve/font_awesome/css/font-awesome.css"
          * do not change href="_themes/basic/css/theme.css"
        """
        len_target = len(target)
        idx = s.find(target)
        while idx > 0:
            idx2 = s.find('"', idx + 6)
            assert idx2 > idx
            sub = s[idx + len_target:idx2]
            if sub and ('://' in sub or sub[0] in '+_#' or sub.startswith('static')):
                idx = s.find(target, idx2)
                continue
            start = s[:idx + len_target]
            end = s[idx2:]
            sub = sub.replace('/', SLASH)
            s = start + sub + end
            idx = s.find(target, idx2)
        return s
