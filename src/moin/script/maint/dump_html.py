# Copyright: 2015-2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Creates a static dump of HTML files for each current item in this wiki.

Usage:
    ./m dump-html  <options>  # or windows: m dump-html ...

Alternate Usage (activate the virtual environment):
    moin dump-html <options>

Options:
    --theme=<theme name>
    --directory=<output directory name>  # name with / means full path, else under moin root directory
    --exclude-ns=<comma separated list of namespaces to exclude>
    --query=<item name or regex to select items>

Defaults:
    --theme=topside_cms
    --directory=<install root dir>HTML
    --exclude-ns=userprofiles

Works best with a CMS-like theme that excludes the wiki navigation links for login, edit,
etc. that are not useful within a static HTML dump.

Most html-formatted files created in the root (HTML) directory will not have names
ending with .html, just as the paths used by the wiki server do not end with .html
(e.g. http://127.0.0.1/Home). All browsers tested follow links to pages not
having .html suffixes without complaint.

Duplicate copies of the home page and index page are created with names ending with .html.

Items with media content types and names ending in common media suffixes (.png, .svg, .mp4...)
will have their raw data, not HTML formatted pages, stored in the root HTML directory. All browsers
tested view HTML formatted pages with names ending in common media suffixes as corrupt files.

The raw data of all items are stored in the +get subdirectory.
"""

import sys
import os
import shutil
import re

from flask import current_app as app
from flask import g as flaskg
from flask_script import Command, Option

from whoosh.query import Every, Term, And, Wildcard, Regex

from werkzeug.exceptions import Forbidden

from xstatic.main import XStatic

from MoinMoin.apps.frontend.views import show_item
from MoinMoin.app import before_wiki
from MoinMoin.constants.keys import CURRENT, THEME_NAME, NAME_EXACT, WIKINAME
from MoinMoin.constants.contenttypes import CONTENTTYPE_MEDIA, CONTENTTYPE_MEDIA_SUFFIX

from wikiconfig import Config

from MoinMoin import log
logging = log.getLogger(__name__)

SLASH = '(2f)'


class Dump(Command):
    description = 'Create a static HTML image of this wiki.'

    option_list = [
        Option('--directory', '-d', dest='directory', type=unicode, required=False, default='HTML',
               help='Directory name containing the output files, default HTML'),
        Option('--theme', '-t', dest='theme', required=False, default='topside_cms',
               help='Name of theme used in creating output pages, default topside_cms'),
        Option('--exclude-ns', '-e', dest='exclude_ns', required=False, default='userprofiles',
               help='Comma separated list of excluded namespaces, default userprofiles'),
        Option('--query', '-q', dest='query', required=False, default=None,
               help='name or regex of items to be included'),
    ]

    def run(self, directory='HTML', theme='topside_cms', exclude_ns='userprofiles', user=None, query=None):
        if theme:
            app.cfg.user_defaults[THEME_NAME] = theme
        exclude_ns = exclude_ns.split(',') if exclude_ns else []

        before_wiki()

        norm = os.path.normpath
        join = os.path.join

        if '/' in directory:
            # user has specified complete path to root
            html_root = directory
        else:
            html_root = norm(join(app.cfg.wikiconfig_dir, directory))
        repo_root = norm(join(app.cfg.wikiconfig_dir))
        moinmoin = norm(join(app.cfg.wikiconfig_dir, 'MoinMoin'))

        # override ACLs with permission to read all items
        for namespace, acls in app.cfg.acl_mapping:
            acls['before'] = 'All:read'

        # create an empty output directory after deleting any existing directory
        print u'Creating output directory {0}, starting to copy supporting files'.format(html_root)
        if os.path.exists(html_root):
            shutil.rmtree(html_root, ignore_errors=False)
        else:
            os.makedirs(html_root)

        # create subdirectories and copy static css, icons, images into "static" subdirectory
        shutil.copytree(norm(join(moinmoin, 'static')), norm(join(html_root, 'static')))
        shutil.copytree(norm(join(repo_root, 'wiki_local')), norm(join(html_root, '+serve/wiki_local')))

        # copy files from xstatic packaging into "+serve" subdirectory
        pkg = Config.pkg
        xstatic_dirs = ['font_awesome', 'jquery', 'jquery_tablesorter', 'autosize']
        if theme in ['basic', ]:
            xstatic_dirs.append('bootstrap')
        for dirs in xstatic_dirs:
            xs = XStatic(getattr(pkg, dirs), root_url='/static', provider='local', protocol='http')
            shutil.copytree(xs.base_dir, norm(join(html_root, '+serve', dirs)))

        # copy directories for theme's static files
        theme = app.cfg.user_defaults[THEME_NAME]
        if theme == 'topside_cms':
            # topside_cms uses topside CSS files
            from_dir = norm(join(moinmoin, 'themes/topside/static'))
        else:
            from_dir = norm(join(moinmoin, 'themes', theme, 'static'))
        to_dir = norm(join(html_root, '_themes', theme))
        shutil.copytree(from_dir, to_dir)

        # convert: <img alt="svg" src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg" />
        # to:      <img alt="svg" src="+get/svg" />
        invalid_src = re.compile(r' src="/\+get/\+[0-9a-f]{32}/')
        valid_src = u' src="+get/'

        # get ready to render and copy individual items
        names = []
        home_page = None
        get_dir = norm(join(html_root, '+get'))  # images and other raw data from wiki content
        os.makedirs(get_dir)

        if query:
            q = And([Term(WIKINAME, app.cfg.interwikiname), Regex(NAME_EXACT, query)])
        else:
            q = Every()

        print 'Starting to dump items'
        for current_rev in app.storage.search(q, limit=None, sortedby="name"):
            if current_rev.namespace in exclude_ns:
                # we usually do not copy userprofiles, no one can login to a static wiki
                continue
            if not current_rev.name:
                # TODO: we skip nameless tickets, but named tickets and comments are processed with ugly names
                continue

            try:
                item_name = current_rev.fqname.fullname
                rendered = show_item(item_name, CURRENT)  # @@@  userid is needed for acls here
                # convert / characters in sub-items and namespaces and save names for index
                file_name = item_name.replace('/', SLASH)
                filename = norm(join(html_root, file_name))
                names.append(file_name)
            except Forbidden:
                print u'Failed to dump {0}: Forbidden'.format(current_rev.name)
                continue
            except KeyError:
                print u'Failed to dump {0}: KeyError'.format(current_rev.name)
                continue

            if not isinstance(rendered, unicode):
                print u'Rendering failed for {0} with response {1}'.format(file_name, rendered)
                continue
            # make hrefs relative to current folder
            rendered = rendered.replace('href="/', 'href="')
            rendered = rendered.replace('src="/static/', 'src="static/')
            rendered = rendered.replace('src="/+serve/', 'src="+serve/')
            rendered = rendered.replace('href="+index/"', 'href="+index"')  # trailing slash changes relative position
            rendered = rendered.replace('<a href="">', u'<a href="{0}">'.format(app.cfg.default_root))  # TODO: fix basic theme
            # remove item ID from: src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg"
            rendered = re.sub(invalid_src, valid_src, rendered)
            rendered = self.subitems(rendered)

            # copy raw data for all items to output /+get directory; images are required, text items are of marginal/no benefit
            item = app.storage[current_rev.name]
            rev = item[CURRENT]
            with open(get_dir + '/' + file_name, 'wb') as f:
                shutil.copyfileobj(rev.data, f)

            # save rendered items or raw data to dump directory root
            contenttype = item.meta['contenttype'].split(';')[0]
            if contenttype in CONTENTTYPE_MEDIA and filename.endswith(CONTENTTYPE_MEDIA_SUFFIX):
                # do not put a rendered html-formatted file with a name like video.mp4 into root; browsers want raw data
                with open(filename, 'wb') as f:
                    rev.data.seek(0)
                    shutil.copyfileobj(rev.data, f)
                    print u'Saved file named {0} as raw data'.format(filename).encode('utf-8')
            else:
                with open(filename, 'wb') as f:
                    f.write(rendered.encode('utf8'))
                    print u'Saved file named {0}'.format(filename).encode('utf-8')

            if current_rev.name == app.cfg.default_root:
                # make duplicates of home page that are easy to find in directory list and open with a click
                for target in [(current_rev.name + '.html'), ('_' + current_rev.name + '.html')]:
                    with open(norm(join(html_root, target)), 'wb') as f:
                        f.write(rendered.encode('utf8'))
                home_page = rendered  # save a copy for creation of index page

        if home_page:
            # create an index page by replacing the content of the home page with a list of items
            # work around differences in basic and modernized theme layout
            # TODO: this is likely to break as new themes are added
            if theme == 'basic':
                start = '<div class="moin-content" role="main">'  # basic
                end = '<footer class="navbar moin-footer">'
                div_end = '</div>'
            else:
                start = '<div id="moin-content">'  # modernized , topside, topside cms
                end = '<footer id="moin-footer">'
                div_end = '</div></div>'
            # build a page named "+index" containing links to all wiki items
            ul = u'<h1>Index</h1><ul>{0}</ul>'
            li = u'<li><a href="{0}">{1}</a></li>'
            links = []
            names.sort()
            for name in names:
                links.append(li.format(name, name.replace(SLASH, '/')))
            name_links = ul.format(u'\n'.join(links))
            try:
                part1 = home_page.split(start)[0]
                part2 = home_page.split(end)[1]
                page = part1 + start + name_links + div_end + end + part2
            except IndexError:
                page = home_page
                print u'Error: failed to find {0} in item named {1}'.format(end, app.cfg.default_root)
            for target in ['+index', '_+index.html']:
                with open(norm(join(html_root, target)), 'wb') as f:
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
