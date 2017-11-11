# Copyright: 2015-2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Creates a static dump of HTML files for each current item in this wiki.

Usage (activate the virtual environment):
    moin dump-html --theme=topside_cms --directory=HTML

    where:
        --directory specifies output location, defaults to HTML
        --theme specifies theme, defaults to wikiconfig theme_default value

Alternate Usage that will use defaults shown above:
    ./m dump-html  # windows: m dump-html

Works best with a CMS-like theme that suppresses the wiki navigation links for login, edit,
etc. that are not useful within a static HTML dump.

The html-formatted files created in the root (HTML) directory will not have names
ending with .html, just as the paths used by the wiki server do not end with .html
(e.g. http://127.0.0.1/Home). All browsers tested follow links
to pages not having .html suffixes without complaint.

Duplicate copies of the home page and index page are created with names ending with .html.

The raw data of all items is stored in the +get subdirectory.

TODO:
    * add feature to accept userid and password options (in case items are protected with ACLs)
    * add feature to limit output to selected pages
    * add feature to include/exclude namespaces: users, etc.
        * (userprofiles namespace is suppressed as data is of no value here)
    * fix issues related to missing or misleading filename suffixes. Using data from contrib/sample/:
        * all browsers think the audio.mp3 and video.mp4 html files in the root directory are corrupt
            * an .html suffix is needed
              or, the creation of these "html" files should be suppressed because the
              actual media files with the same name are in the +get sub-directory
        * all browsers fail to display the svg image file, a .svg suffix is needed on the /+get/svg file
        * the solution may be to store only image and media files in HTML/+get/ and remove
          files of the same name from HTML/
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
        html_root = os.path.dirname(os.path.abspath(__file__)) + u'/../../../{0}/'.format(directory)
        repo_root = os.path.dirname(os.path.abspath(__file__)) + u'/../../../'
        moin_root = os.path.dirname(os.path.abspath(__file__)) + u'/../../'

        # make an empty output directory, default name is HTML
        print u'Creating output directory {0}, starting to copy supporting files'.format(html_root)
        if os.path.exists(html_root):
            shutil.rmtree(html_root, ignore_errors=False)
        else:
            os.makedirs(html_root)

        # create subdirectories and copy static css, icons, images into "static" subdirectory
        shutil.copytree(moin_root + '/static', html_root + 'static')
        shutil.copytree(repo_root + '/wiki_local', html_root + '+serve/wiki_local')

        # copy files from xstatic packaging into "+serve" subdirectory
        pkg = Config.pkg
        # TODO: add option to not load bootstrap
        xstatic_dirs = ['font_awesome', 'jquery', 'jquery_tablesorter', ]
        if theme in ['basic', ]:
            xstatic_dirs.append('bootstrap')
        for dirs in xstatic_dirs:
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

        # get ready to render and copy individual items
        names = []
        home_page = None
        get_dir = html_root + '/+get'  # images and other raw data from wiki content
        os.makedirs(get_dir)

        print 'Starting to dump items'
        for current_rev in app.storage.search(Every(), limit=None):
            # do not copy userprofiles, no one can login to a static wiki
            if current_rev.namespace == 'userprofiles':
                continue

            # remove / characters from sub-item filenames
            if current_rev.name:
                file_name = current_rev.name.replace('/', SLASH)
                filename = html_root + file_name
            else:
                # TODO: we skip nameless tickets, but named tickets and comments are processed with ugly names
                continue

            try:
                if current_rev.namespace:
                    item_name = current_rev.namespace + '/' + current_rev.name
                else:
                    item_name = current_rev.name
                rendered = show_item(item_name, CURRENT)
                names.append(file_name)  # build index containing items successfully rendered
            except Forbidden:  # Forbidden
                print 'Failed to dump %s: Forbidden' % current_rev.name
                continue
            except KeyError:  # Forbidden
                print 'Failed to dump %s: KeyError' % current_rev.name
                continue

            if not isinstance(rendered, unicode):
                print 'Rendering failed for {0} with response {1}'.format(file_name, rendered)
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
                print u'Saved file named {0}'.format(filename).encode('utf-8')
            if current_rev.name == app.cfg.default_root:
                # make duplicates of home page that are easy to find in directory list and open with a click
                for target in [current_rev.name + '.html', '_' + current_rev.name + '.html']:
                    with open(html_root + target, 'wb') as f:
                        f.write(rendered.encode('utf8'))
                home_page = rendered  # save a copy for creation of index page

            # copy raw data for all items to output; images are required, text items are of marginal/no benefit
            item = app.storage[current_rev.name]
            rev = item[CURRENT]
            with open(get_dir + '/' + file_name, 'wb') as df:
                shutil.copyfileobj(rev.data, df)

        if home_page:
            # create an index page by replacing the content of the home page with a list of items
            # work around differences in basic and modernized theme layout
            # TODO: this is likely to break as new themes are added
            if theme == 'basic':
                start = '<div class="moin-content" role="main">'  # basic
                end = '<footer class="navbar moin-footer">'
            else:
                start = '<div id="moin-content">'  # modernized , topside, topside cms
                end = '<footer id="moin-footer">'
            div_end = '</div></div>'
            # build a page named "+index" containing links to all wiki items
            ul = '<h1>Index</h1><ul>%s</ul>'
            li = '<li><a href="%s">%s</a></li>'
            links = []
            names.sort()
            for name in names:
                links.append(li % (name, name.replace(SLASH, '/')))
            name_links = ul % ('\n'.join(links))
            try:
                part1 = home_page.split(start)[0]
                part2 = home_page.split(end)[1]
                page = part1 + start + name_links + div_end + end + part2
            except IndexError:
                page = home_page
                print 'Error: failed to find {0} in item named {1}'.format(end, app.cfg.default_root)
            for target in ['+index', '_+index.html']:
                with open(html_root + target, 'wb') as f:
                    f.write(page.encode('utf8'))
        else:
            print 'Error: no item matching name in app.cfg.default_root was found'

    def subitems(self, s, target='href="'):
        """
        fix links to subitems
          * <a href="Home/subitem"> becomes <a href="Home(2f)subitem">
          * do not change href="https://moinmo.in/FrontPage"
          * do not change href="+serve/font_awesome/css/font-awesome.css"
          * do not change href="_themes/topside_cms/css/theme.css"
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
