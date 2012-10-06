# Copyright: 2003-2010 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:RadomirDopieralski
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Theme Support
"""


import urllib

from json import dumps
from operator import attrgetter

from flask import current_app as app
from flask import g as flaskg
from flask import url_for, request
from flask.ext.themes import get_theme, render_theme_template

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.i18n import _, L_, N_
from MoinMoin import wikiutil, user
from MoinMoin.config import USERID, ADDRESS, HOSTNAME
from MoinMoin.search import SearchForm
from MoinMoin.util.interwiki import split_interwiki, getInterwikiHome, is_local_wiki, is_known_wiki, url_for_item
from MoinMoin.util.crypto import cache_key
from MoinMoin.util.forms import make_generator
from MoinMoin.util.clock import timed
from MoinMoin.util.mime import Type


def get_current_theme():
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, 'user', None)
    if u and u.theme_name is not None:
        theme_name = u.theme_name
    else:
        theme_name = app.cfg.theme_default
    try:
        return get_theme(theme_name)
    except KeyError:
        logging.warning("Theme {0!r} was not found; using default of {1!r} instead.".format(theme_name, app.cfg.theme_default))
        theme_name = app.cfg.theme_default
        return get_theme(theme_name)


@timed()
def render_template(template, **context):
    return render_theme_template(get_current_theme(), template, **context)

def themed_error(e):
    item_name = request.view_args.get('item_name', u'')
    if e.code == 403:
        title = L_('Access denied')
        description = L_('You are not allowed to access this resource.')
    else:
        # if we have no special code, we just return the HTTPException instance
        return e
    content = render_template('error.html',
                              item_name=item_name,
                              title=title, description=description)
    return content, e.code


class ThemeSupport(object):
    """
    Support code for template feeding.
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.user = flaskg.user
        self.storage = flaskg.storage
        self.ui_lang = 'en' # XXX
        self.ui_dir = 'ltr' # XXX
        self.content_lang = flaskg.content_lang # XXX
        self.content_dir = 'ltr' # XXX
        self.meta_items = [] # list of (name, content) for html head <meta>

    def location_breadcrumbs(self, item_name):
        """
        Assemble the location using breadcrumbs (was: title)

        :rtype: list
        :returns: location breadcrumbs items in tuple (segment_name, item_name, exists)
        """
        breadcrumbs = []
        current_item = ''
        for segment in item_name.split('/'):
            current_item += segment
            breadcrumbs.append((segment, current_item, self.storage.has_item(current_item)))
            current_item += '/'
        return breadcrumbs

    def path_breadcrumbs(self):
        """
        Assemble the path breadcrumbs (a.k.a.: trail)

        :rtype: list
        :returns: path breadcrumbs items in tuple (wiki_name, item_name, url, exists, err)
        """
        user = self.user
        breadcrumbs = []
        trail = user.get_trail()
        for interwiki_item_name in trail:
            wiki_name, item_name = split_interwiki(interwiki_item_name)
            err = not is_known_wiki(wiki_name)
            href = url_for_item(item_name, wiki_name=wiki_name)
            if is_local_wiki(wiki_name):
                exists = self.storage.has_item(item_name)
                wiki_name = ''  # means "this wiki" for the theme code
            else:
                exists = True  # we can't detect existance of remote items
            breadcrumbs.append((wiki_name, item_name, href, exists, err))
        return breadcrumbs

    def subitem_index(self, item_name):
        """
        Get a list of subitems for the given item_name

        :rtype: list
        :returns: list of item tuples (item_name, item_title, item_mime_type, has_children)
        """
        from MoinMoin.items import Item
        item = Item.create(item_name)
        return item.get_mixed_index()

    def userhome(self):
        """
        Assemble arguments used to build user homepage link

        :rtype: tuple
        :returns: arguments of user homepage link in tuple (wiki_href, aliasname, title, exists)
        """
        user = self.user
        name = user.name
        aliasname = user.aliasname
        if not aliasname:
            aliasname = name

        wikiname, itemname = getInterwikiHome(name)
        title = u"{0} @ {1}".format(aliasname, wikiname)
        # link to (interwiki) user homepage
        if is_local_wiki(wikiname):
            exists = self.storage.has_item(itemname)
        else:
            # We cannot check if wiki pages exists in remote wikis
            exists = True
        wiki_href = url_for_item(itemname, wiki_name=wikiname)
        return wiki_href, aliasname, title, exists

    def split_navilink(self, text):
        """
        Split navibar links into pagename, link to page

        Admin or user might want to use shorter navibar items by using
        the [[page|title]] or [[url|title]] syntax.

        Supported syntax:
            * PageName
            * WikiName:PageName
            * wiki:WikiName:PageName
            * url
            * all targets as seen above with title: [[target|title]]

        :param text: the text used in config or user preferences
        :rtype: tuple
        :returns: pagename or url, link to page or url
        """
        title = None
        wiki_local = ''  # means local wiki

        # Handle [[pagename|title]] or [[url|title]] formats
        if text.startswith('[[') and text.endswith(']]'):
            text = text[2:-2]
            try:
                target, title = text.split('|', 1)
                target = target.strip()
                title = title.strip()
            except (ValueError, TypeError):
                # Just use the text as is.
                target = text.strip()
        else:
            target = text

        if wikiutil.is_URL(target):
            if not title:
                title = target
            return target, title, wiki_local

        # remove wiki: url prefix
        if target.startswith("wiki:"):
            target = target[5:]

        wiki_name, item_name = split_interwiki(target)
        if wiki_name == 'Self':
            wiki_name = ''
        href = url_for_item(item_name, wiki_name=wiki_name)
        if not title:
            title = item_name
        return href, title, wiki_name

    @timed()
    def navibar(self, item_name):
        """
        Assemble the navibar

        :rtype: list
        :returns: list of tuples (css_class, url, link_text, title)
        """
        current = item_name
        # Process config navi_bar
        items = [(cls, url_for(endpoint, **args), link_text, title)
                 for cls, endpoint, args, link_text, title in self.cfg.navi_bar]

        # Add user links to wiki links.
        for text in self.user.quicklinks:
            url, link_text, title = self.split_navilink(text)
            items.append(('userlink', url, link_text, title))

        # Add sister pages (see http://usemod.com/cgi-bin/mb.pl?SisterSitesImplementationGuide )
        for sistername, sisterurl in self.cfg.sistersites:
            if is_local_wiki(sistername):
                items.append(('sisterwiki current', sisterurl, sistername))
            else:
                cid = cache_key(usage="SisterSites", sistername=sistername)
                sisteritems = app.cache.get(cid)
                if sisteritems is None:
                    uo = urllib.URLopener()
                    uo.version = 'MoinMoin SisterItem list fetcher 1.0'
                    try:
                        sisteritems = {}
                        f = uo.open(sisterurl)
                        for line in f:
                            line = line.strip()
                            try:
                                item_url, item_name = line.split(' ', 1)
                                sisteritems[item_name.decode('utf-8')] = item_url
                            except:
                                pass # ignore invalid lines
                        f.close()
                        app.cache.set(cid, sisteritems)
                        logging.info("Site: {0!r} Status: Updated. Pages: {1}".format(sistername, len(sisteritems)))
                    except IOError as err:
                        (title, code, msg, headers) = err.args # code e.g. 304
                        logging.warning("Site: {0!r} Status: Not updated.".format(sistername))
                        logging.exception("exception was:")
                if current in sisteritems:
                    url = sisteritems[current]
                    items.append(('sisterwiki', url, sistername, ''))
        return items

    def parent_item(self, item_name):
        """
        Return name of parent item for the current item

        :rtype: unicode
        :returns: parent item name
        """
        parent_item_name = wikiutil.ParentItemName(item_name)
        if item_name and parent_item_name:
            return parent_item_name

    # TODO: reimplement on-wiki-page sidebar definition with MoinMoin.converter

    # Properties ##############################################################

    def login_url(self):
        """
        Return URL usable for user login

        :rtype: unicode (or None, if no login url is supported)
        :returns: url for user login
        """
        url = None
        if self.cfg.auth_login_inputs == ['special_no_input']:
            url = url_for('frontend.login', login=1)
        if self.cfg.auth_have_login:
            url = url or url_for('frontend.login')
        return url


def get_editor_info(meta, external=False):
    addr = meta.get(ADDRESS)
    hostname = meta.get(HOSTNAME)
    text = _('anonymous')  # link text
    title = ''  # link title
    css = 'editor'  # link/span css class
    name = None  # author name
    uri = None  # author homepage uri
    email = None  # pure email address of author
    if app.cfg.show_hosts and addr:
        # only tell ip / hostname if show_hosts is True
        if hostname:
            text = hostname[:15]  # 15 = len(ipaddr)
            name = title = u'{0}[{1}]'.format(hostname, addr)
            css = 'editor host'
        else:
            name = text = addr
            title = u'[{0}]'.format(addr)
            css = 'editor ip'

    userid = meta.get(USERID)
    if userid:
        u = user.User(userid)
        name = u.name
        text = name
        aliasname = u.aliasname
        if not aliasname:
            aliasname = name
        if title:
            # we already have some address info
            title = u"{0} @ {1}".format(aliasname, title)
        else:
            title = aliasname
        if u.mailto_author and u.email:
            email = u.email
            css = 'editor mail'
        else:
            homewiki = app.cfg.user_homewiki
            if is_local_wiki(homewiki):
                css = 'editor homepage local'
            else:
                css = 'editor homepage interwiki'
            uri = url_for_item(name, wiki_name=homewiki, _external=external)

    result = dict(name=name, text=text, css=css, title=title)
    if uri:
        result['uri'] = uri
    if email:
        result['email'] = email
    return result

def shorten_item_name(name, length=25):
    """
    Shorten item names

    Shorten very long item names that tend to break the user
    interface. The short name is usually fine, unless really stupid
    long names are used (WYGIWYD).

    :param name: item name, unicode
    :param length: maximum length for shortened item names, int
    :rtype: unicode
    :returns: shortened version.
    """
    # First use only the sub page name, that might be enough
    if len(name) > length:
        name = name.split('/')[-1]
        # If it's not enough, replace the middle with '...'
        if len(name) > length:
            half, left = divmod(length - 3, 2)
            name = u'{0}...{1}'.format(name[:half + left], name[-half:])
    return name

def shorten_id(name, length=7):
    """
    Shorten IDs to specified length

    Shorten long IDs into just the first <length> characters. There's
    no need to display the whole IDs everywhere.

    :param name: item name, unicode
    :param length: Maximum length of the resulting ID, int
    :rtype: unicode
    :returns: <name> truncated to <length> characters
    """

    return name[:length]

MIMETYPE_TO_CLASS = {
    'application/pdf': 'pdf',
    'application/zip': 'package',
    'application/x-tar': 'package',
    'application/x-gtar': 'package',
    'application/x-twikidraw': 'drawing',
    'application/x-anywikidraw': 'drawing',
    'application/x-svgdraw': 'drawing',
}

def contenttype_to_class(contenttype):
    """
    Convert a contenttype string to a css class.
    """
    cls = MIMETYPE_TO_CLASS.get(contenttype)
    if not cls:
        # just use the major part of mimetype
        cls = contenttype.split('/', 1)[0]
    return 'moin-mime-{0}'.format(cls)


def utctimestamp(dt):
    """
    convert a datetime object (UTC) to a UNIX timestamp (UTC)

    Note: time library writers seem to have a distorted relationship to inverse
          functions and also to UTC (see time.gmtime, see datetime.utcfromtimestamp).
    """
    from calendar import timegm
    return timegm(dt.timetuple())


def setup_jinja_env():
    app.jinja_env.filters['shorten_item_name'] = shorten_item_name
    app.jinja_env.filters['shorten_id'] = shorten_id
    app.jinja_env.filters['contenttype_to_class'] = contenttype_to_class
    app.jinja_env.filters['json_dumps'] = dumps
    # please note that these filters are installed by flask-babel:
    # datetimeformat, dateformat, timeformat, timedeltaformat

    app.jinja_env.globals.update({
                            # please note that flask-babel/jinja2.ext installs:
                            # _, gettext, ngettext
                            'isinstance': isinstance,
                            'list': list,
                            'Type': Type,
                            # please note that flask-themes installs:
                            # theme, theme_static
                            'theme_supp': ThemeSupport(app.cfg),
                            'user': flaskg.user,
                            'storage': flaskg.storage,
                            'clock': flaskg.clock,
                            'cfg': app.cfg,
                            'item_name': 'handlers need to give it',
                            'url_for_item': url_for_item,
                            'get_editor_info': lambda meta: get_editor_info(meta),
                            'utctimestamp': lambda dt: utctimestamp(dt),
                            'gen': make_generator(),
                            'search_form': SearchForm.from_defaults(),
                            })
