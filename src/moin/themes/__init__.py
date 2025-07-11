# Copyright: 2003-2010 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:RadomirDopieralski
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2023-2024 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Theme Support
"""

from __future__ import annotations

from typing import cast, TYPE_CHECKING

import os
import urllib.request
import urllib.parse

from json import dumps

from flask import current_app as app
from flask import g as flaskg
from flask import url_for, request, session, flash
from flask_theme import get_theme, render_theme_template

from babel import Locale

from moin.i18n import _, L_
from moin import wikiutil
from moin.constants.keys import USERID, ADDRESS, HOSTNAME, REVID, ITEMID, NAME_EXACT, ASSIGNED_TO, NAME, NAMESPACE
from moin.constants.contenttypes import CONTENTTYPES_MAP, CONTENTTYPE_MARKUP, CONTENTTYPE_TEXT, CONTENTTYPE_MOIN_19
from moin.constants.misc import FLASH_REPEAT, ICON_MAP
from moin.constants.namespaces import NAMESPACE_DEFAULT, NAMESPACE_USERS, NAMESPACE_USERPROFILES, NAMESPACE_ALL
from moin.constants.rights import SUPERUSER
from moin.search import SearchForm
from moin.user import User
from moin.utils.interwiki import (
    split_interwiki,
    getInterwikiHome,
    is_local_wiki,
    is_known_wiki,
    url_for_item,
    CompositeName,
    split_fqname,
    get_fqname,
)
from moin.utils.forms import make_generator
from moin.utils.clock import timed
from moin.utils.mime import Type
from moin.utils import show_time

from moin import log

if TYPE_CHECKING:
    from moin.config import WikiConfigProtocol
    from moin.storage.middleware.protecting import ProtectingMiddleware

logging = log.getLogger(__name__)


def get_current_theme():
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, "user", None)
    if u and u.theme_name is not None:
        theme_name = u.theme_name
    else:
        theme_name = app.cfg.theme_default
    try:
        return get_theme(theme_name)
    except KeyError:
        logging.warning(f"Theme {theme_name!r} was not found; using default of {app.cfg.theme_default!r} instead.")
        theme_name = app.cfg.theme_default
        return get_theme(theme_name)


def render_template(template, **context):
    return render_theme_template(get_current_theme(), template, **context)


def themed_error(e):
    item_name = request.view_args.get("item_name", "")
    if e.code == 403:
        title = L_("Item not found or access denied")
        description = L_("Item '{name}' does not exist or you do not have permission to access it.").format(
            name=item_name
        )
        if e.description.startswith(" "):
            # leading blank indicates supplemental info, not standard werkzeug message
            description += e.description
    else:
        # if we have no special code, we just return the HTTPException instance
        return e
    content = render_template("error.html", item_name=item_name, title=title, description=description)
    return content, e.code


class ThemeSupport:
    """
    Support code for template feeding.
    """

    def __init__(self, cfg: WikiConfigProtocol):
        self.cfg = cfg
        self.user = cast(User, flaskg.user)
        self.storage = cast("ProtectingMiddleware", flaskg.storage)
        self.ui_lang = cfg.language_default
        self.ui_dir = cfg.content_dir
        self.user_lang = flaskg.user.language or self.ui_lang
        self.user_dir = Locale(self.user_lang).text_direction
        if request.url_root[len(request.host_url) : -1]:
            self.wiki_root = "/" + request.url_root[len(request.host_url) : -1]
        else:
            self.wiki_root = ""
        if FLASH_REPEAT in session:
            for msg, level in session[FLASH_REPEAT]:
                flash(msg, level)
            del session[FLASH_REPEAT]

    def get_fullname(self, meta):
        """
        Convert list of names to list of fullnames: <namespace>/<name> or <name>

        :rtype: tuple
        :returns: list of item names with namespace prefix or item names if default namespace
        """
        fullname = (name if not meta[NAMESPACE] else meta[NAMESPACE] + "/" + name for name in meta[NAME])
        return fullname

    def field_term(self, field, term):
        """
        Convert Whoosh stored bytes term to string, enables display of matching search terms by hit.
        """
        try:
            term = term.decode()
        except UnicodeDecodeError:
            try:
                # Whoosh converts datetime and integers to bytes using custom algorithms to compress bytes
                # We use the request url to retrieve the terms for mtime and rev_number
                # The request urls for short form searches and ajax searches are similar to the following:
                # http://127.0.0.1:5000/+search?q=mtime%3A2022+rev_number%3A2
                # http://127.0.0.1:5000/+search?q=mtime%3A2022-02&history=false&time_sorting=default&filetypes=all
                #     %2C&boolajax=true&is_ticket= HTTP/1.1
                url = request.url
                url = urllib.parse.unquote(url)
                args = url.split("?q=")[1]
                args = args.split("&")[0]
                if "+" in args:
                    terms = args.split("+")
                elif " " in args:
                    terms = args.split()
                else:
                    terms = [args]
                for keyval in terms:
                    fld, trm = keyval.split(":")
                    if fld == "mtime" == field:
                        return fld, trm
                    elif fld == "rev_number" == field:
                        return fld, trm
                term = "unknown"
            except Exception:
                term = "unknown"
        return field, term

    def get_action_tabs(self, fqname, current_endpoint):
        """
        Create a list of commonly used item views. Used by Basic theme.

        :rtype: list
        :returns: list of item views
        """

        if not fqname or not fqname.value:
            return []

        # TODO: Need to add fqname support to has_item in indexing.py
        exists = bool(flaskg.storage.get_item(**fqname.query))

        navtabs_endpoints = [
            "frontend.show_item",
            "frontend.history",
            "frontend.show_item_meta",
            "frontend.highlight_item",
            "frontend.backrefs",
            "frontend.index",
            "frontend.sitemap",
            "frontend.similar_names",
        ]

        if self.user.may.write(fqname):  # TODO: use new may function
            navtabs_endpoints.append("frontend.modify_item")

        navtabs = []
        spl_active = [("frontend.history", "frontend.diff")]

        for endpoint, label, title, check_exists in self.cfg.item_views:
            if endpoint not in self.cfg.endpoints_excluded:
                if not check_exists or exists:
                    if endpoint in navtabs_endpoints:

                        iconcls = ICON_MAP[endpoint] if endpoint in ICON_MAP else ""
                        linkcls = None

                        if endpoint == "special.comments":
                            maincls = "moin-toggle-comments-button"
                            href = "#"
                        elif endpoint == "special.transclusions":
                            maincls = "moin-transclusions-button"
                            href = "#"
                        else:
                            maincls = None
                            # special case for modify item link, this depends on the double click to edit JS
                            if endpoint == "frontend.modify_item":
                                linkcls = "moin-modify-button"
                            href = url_for(endpoint, item_name=fqname)
                            if endpoint == current_endpoint or (endpoint, current_endpoint) in spl_active:
                                maincls = "active"

                        navtabs.append((endpoint, href, maincls, iconcls, linkcls, title, label))
        return navtabs

    def get_local_panel(self, fqname):
        """
        Split uncommonly used cfg.item views into user actions, item actions, and view options.

        :rtype: list
        :returns: list of lists containing: user actions, item actions, and view options for Basic theme
        """

        if not fqname:
            return [], [], []

        item = flaskg.storage.get_item(**fqname.query)

        if not item:
            return [], [], []

        user_actions_endpoints = ["frontend.quicklink_item", "frontend.subscribe_item"]
        item_navigation_endpoints = ["special.supplementation"]
        item_actions_endpoints = (
            [
                "frontend.rename_item",
                "frontend.delete_item",
                "frontend.destroy_item",
                "frontend.download_item",
                "frontend.convert_item",
                "frontend.copy_item",
            ]
            if self.user.may.write(fqname)
            else []
        )

        user_actions = []
        item_navigation = []
        item_actions = []

        for endpoint, label, title, check_exists in self.cfg.item_views:
            if endpoint not in self.cfg.endpoints_excluded:
                if not check_exists or item:
                    if endpoint in user_actions_endpoints:
                        if flaskg.user.valid:
                            href = url_for(endpoint, item_name=fqname)
                            iconcls = ICON_MAP[endpoint] if endpoint in ICON_MAP else ""
                            # endpoint = iconcls = label = None

                            if endpoint == "frontend.quicklink_item":
                                if not flaskg.user.is_quicklinked_to([fqname]):
                                    label = _("Add Link")
                                else:
                                    label = _("Remove Link")
                                user_actions.append((endpoint, href, iconcls, label, title, True))
                            elif endpoint == "frontend.subscribe_item":
                                if flaskg.user.is_subscribed_to(item.item):
                                    label = _("Unsubscribe")
                                else:
                                    label = _("Subscribe")
                                user_actions.append((endpoint, href, iconcls, label, title, True))

                    elif endpoint in item_actions_endpoints:

                        iconcls = ICON_MAP[endpoint] if endpoint in ICON_MAP else ""

                        href = url_for(endpoint, item_name=fqname)
                        item_actions.append((endpoint, href, iconcls, label, title, True))

                    # Special Supplementation defined only for named items
                    elif endpoint in item_navigation_endpoints and fqname.field == NAME_EXACT:

                        iconcls = ICON_MAP[endpoint] if endpoint in ICON_MAP else ""

                        if endpoint == "special.supplementation":
                            for sub_item_name in self.cfg.supplementation_item_names:
                                current_sub = fqname.value.rsplit("/", 1)[-1]
                                if current_sub not in self.cfg.supplementation_item_names:
                                    supp_name = f"{fqname.value}/{sub_item_name}"
                                    if flaskg.storage.has_item(supp_name) or flaskg.user.may.write(supp_name):
                                        subitem_exists = self.storage.has_item(supp_name)
                                        href = url_for("frontend.show_item", item_name=supp_name)
                                        label = _(sub_item_name)
                                        title = None

                                        item_navigation.append((endpoint, href, iconcls, label, title, subitem_exists))
                        else:
                            href = url_for(endpoint, item_name=fqname)
                            item_navigation.append((endpoint, href, iconcls, label, title, True))

        return user_actions, item_navigation, item_actions

    def get_endpoint_iconmap(self):
        """kept for compatibility reasons, may be used in custom templates"""
        return ICON_MAP

    def location_breadcrumbs(self, fqname):
        """
        Split the incoming fqname into segments. Reassemble into a list of tuples.
        If the fqname has a namespace, the first tuple's segment_name will have the
        namespace as a prefix.

        :rtype: list
        :returns: location breadcrumbs items in tuple (segment_name, fq_name)
        """
        breadcrumbs = []
        current_item = ""
        if not isinstance(fqname, CompositeName):
            fqname = split_fqname(fqname)
        if fqname.field != NAME_EXACT:
            return [(fqname, fqname)]
        namespace = segment1_namespace = fqname.namespace
        item_name = fqname.value
        if not item_name:
            return breadcrumbs
        for segment in item_name.split("/"):
            current_item += segment
            fq_current = CompositeName(namespace, NAME_EXACT, current_item)
            fq_segment = CompositeName(segment1_namespace, NAME_EXACT, segment)
            breadcrumbs.append((fq_segment, fq_current))
            current_item += "/"
            segment1_namespace = ""
        return breadcrumbs

    def path_breadcrumbs(self):
        """
        Assemble the path breadcrumbs (a.k.a.: trail)

        :rtype: list
        :returns: path breadcrumbs items in tuple (wiki_name, item_name, url, aliases, err)
        """
        user = self.user
        breadcrumbs = []
        trail = user.get_trail()
        for interwiki_item_name, aliases in trail:
            wiki_name, namespace, field, item_name = split_interwiki(interwiki_item_name)
            fqname = CompositeName(namespace, field, item_name)
            err = not is_known_wiki(wiki_name)
            href = url_for_item(wiki_name=wiki_name, **fqname.split)
            if is_local_wiki(wiki_name):
                wiki_name = ""  # means "this wiki" for the theme code
            if item_name:
                breadcrumbs.append((wiki_name, fqname, href, aliases, err))
        return breadcrumbs

    def userhome(self):
        """
        Assemble arguments used to build user homepage link

        :rtype: tuple
        :returns: arguments of user homepage link in tuple (wiki_href, display_name, title, exists)
        """
        user = self.user
        name = user.name0
        display_name = user.display_name or name
        wikiname, itemname = getInterwikiHome(name)
        title = f"{display_name} @ {wikiname}"
        # link to (interwiki) user homepage
        if is_local_wiki(wikiname):
            exists = self.storage.has_item(itemname)
        else:
            # We cannot check if wiki pages exists in remote wikis
            exists = True
        wiki_href = url_for_item(itemname, wiki_name=wikiname)
        return wiki_href, display_name, title, exists

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
        wiki_local = ""  # means local wiki

        # Handle [[pagename|title]] or [[url|title]] formats
        if text.startswith("[[") and text.endswith("]]"):
            text = text[2:-2]
            try:
                target, title = text.split("|", 1)
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

        wiki_name, namespace, field, item_name = split_interwiki(target)
        if wiki_name == "Self":
            wiki_name = ""
        href = url_for_item(item_name, namespace=namespace, wiki_name=wiki_name, field=field)
        if not title:
            title = shorten_fqname(CompositeName(namespace, field, item_name))
        return href, title, wiki_name

    @timed()
    def navibar(self, fqname: CompositeName | str):
        """
        Assemble the navibar

        :rtype: list
        :returns: list of tuples (css_class, url, link_text, title)
        """
        if not isinstance(fqname, CompositeName):
            fqname = split_fqname(fqname)
        # Process config navi_bar
        items = []
        for cls, endpoint, args, link_text, title in self.cfg.navi_bar:
            if endpoint == "frontend.show_root":
                endpoint = "frontend.show_item"
                root_fqname = fqname.get_root_fqname()
                default_root = self.cfg.root_mapping.get(NAMESPACE_DEFAULT, self.cfg.default_root)
                args["item_name"] = root_fqname.fullname if fqname.namespace != NAMESPACE_ALL else default_root
                # override link_text to show untranslated <default_root> itemname or <namespace>/<default_root>
                link_text = args["item_name"]
            elif endpoint in ["frontend.global_history", "frontend.global_tags"]:
                args["namespace"] = fqname.namespace
                if fqname and fqname.namespace:
                    link_text = f"{fqname.namespace}/{link_text}"
            elif endpoint == "frontend.index":
                args["item_name"] = fqname.namespace
                if fqname and fqname.namespace:
                    link_text = f"{fqname.namespace}/{link_text}"
            elif endpoint == "admin.index" and not getattr(flaskg.user.may, SUPERUSER)():
                continue
            iconcls = ICON_MAP[endpoint] if endpoint in ICON_MAP else ""
            items.append((cls, url_for(endpoint, **args), link_text, title, iconcls))
        # Add user links to wiki links.
        for text in self.user.quicklinks:
            url, link_text, title = self.split_navilink(text)
            items.append(("userlink", url, link_text, title, ""))
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

    def parentnames(self, names):
        """
        Compute list of parent names (same order as in names, but no dupes)
        Copied from indexing.py

        :param names: item NAME from whoosh index, where NAME is a list
        :return: parent names (list of unicode)
        """
        # must import here to avoid circular import error
        from moin.storage.middleware.indexing import parent_names

        return parent_names(names)

    # Properties ##############################################################

    def login_url(self):
        """
        Return URL usable for user login

        :rtype: unicode (or None, if no login url is supported)
        :returns: url for user login
        """
        url: str | None = None
        if self.cfg.auth_login_inputs == ["special_no_input"]:
            url = url_for("frontend.login", login=1)
        if self.cfg.auth_have_login:
            url = url or url_for("frontend.login")
        return url

    def get_namespaces(self):
        """
        Return a sorted list of tuples (namespace name, fq name of ns home item).

        The special userprofiles NS is omitted because it can never be selected
        by a wiki user.
        """
        namespace_root_mapping: list[tuple[str, CompositeName]] = []
        for namespace, _unused in self.cfg.namespace_mapping:
            if namespace == NAMESPACE_USERPROFILES:
                continue
            namespace = namespace.rstrip("/")
            fq_namespace = CompositeName(namespace, NAME_EXACT, "")
            namespace_root_mapping.append((namespace or "~", fq_namespace.get_root_fqname()))
        return sorted(namespace_root_mapping)

    def item_exists(self, itemname: str):
        """
        Check whether the item pointed to by the given itemname exists or not

        :rtype: boolean
        :returns: whether item pointed to by the link exists or not
        """
        return self.storage.has_item(itemname)

    def itemlink_exists(self, itemlink: str):
        """
        Check whether the item pointed to by the given itemlink exists or not

        :rtype: boolean
        :returns: whether item pointed to by the link exists or not
        """
        item_name = itemlink
        info = app.link_analyzer(item_name)
        if not info.is_valid:
            return False
        if info.is_global:
            return True
        if info.item_name:
            item_name = info.item_name
        return self.item_exists(item_name)

    def variables_css(self):
        """
        Check whether this theme has a variables.css file

        :rtype: boolean
        :returns: whether variables.css file exists or not
        """
        path = os.path.join(get_current_theme().path, "static/css/variables.css")
        return os.path.isfile(path)

    def is_markup_or_text(self, contenttype):
        """
        Return true if contenttype is markup or text-like.

        Any text-like item may be converted to a type having an "out" converter.
        """
        return contenttype in CONTENTTYPE_MARKUP + CONTENTTYPE_TEXT + CONTENTTYPE_MOIN_19


def get_editor_info(meta, external=False):
    """
    Create a dict of formatted user info.

    :rtype: dict
    :returns: dict of formatted user info such as name, ip addr, email,...
    """
    addr = meta.get(ADDRESS)
    hostname = meta.get(HOSTNAME)
    text = _("anonymous")  # link text
    title = ""  # link title
    css = "editor"  # link/span css class
    name = None  # author name
    uri = None  # author homepage uri
    email = None  # pure email address of author
    if app.cfg.show_hosts and addr:
        # only tell ip / hostname if show_hosts is True
        if hostname:
            text = hostname[:15]  # 15 = len(ipaddr)
            name = title = f"{hostname}[{addr}]"
            css = "editor host"
        else:
            name = text = addr
            title = f"[{addr}]"
            css = "editor ip"

    userid = meta.get(USERID)
    if userid:
        u = User(userid)
        name = u.name0
        text = u.display_name or name
        display_name = u.display_name or name
        if title:
            # we already have some address info
            title = f"{display_name} @ {title}"
        else:
            title = display_name
        if u.mailto_author and u.email:
            email = u.email
            css = "editor mail"
        else:
            homewiki = app.cfg.user_homewiki
            if is_local_wiki(homewiki):
                css = "editor homepage local"
            else:
                css = "editor homepage interwiki"
            uri = url_for_item(name, wiki_name=homewiki, _external=external, namespace=NAMESPACE_USERS)

    result = dict(name=name, text=text, css=css, title=title)
    if uri:
        result["uri"] = uri
    if email:
        result["email"] = email
    return result


def get_assigned_to_info(meta):
    display_name = ""
    userid = meta.get(ASSIGNED_TO)
    if userid:
        u = User(userid)
        display_name = u.display_name or u.name0
    return display_name


def shorten_fqname(fqname, length=25):
    """
    Shorten a given long fqname so that it looks good depending upon whether
    the field is a UUID or not.

    :param fqname: fqname, namedtuple
    :param length: maximum length for shortened fqnames in case the field is not a UUID.
    :rtype: unicode
    :returns: shortened fqname.
    """
    if fqname.namespace and fqname.field in (REVID, ITEMID):
        # users/@itemid12345678901234567890...12 > users/1234567
        return fqname.namespace + "/" + shorten_id(fqname.value)
    name = fqname.fullname
    if len(name) > length:
        if fqname.field in [REVID, ITEMID]:
            name = shorten_id(name)
        else:
            name = shorten_item_name(name, length)
    return name


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
        name_part = name.split("/")[-1]
        # If it's not enough, replace the middle with '...'
        if len(name_part) > length:
            half, left = divmod(length - 3, 2)
            name = f"{name_part[:half + left]}...{name_part[-half:]}"
        elif len(name_part) < length - 6:
            # now it is too short, add back starting characters
            name = f"{name[:length - len(name_part) - 3]}...{name_part}"
        else:
            name = name_part
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
    if name.startswith("@itemid/"):
        return name[8 : 8 + length]
    return name[:length]


MIMETYPE_TO_CLASS = {
    "application/pdf": "pdf",
    "application/zip": "package",
    "application/x-tar": "package",
    "application/x-gtar": "package",
    "application/x-svgdraw": "drawing",
}


def contenttype_to_class(contenttype):
    """
    Convert a contenttype string to a css class.
    """
    cls = MIMETYPE_TO_CLASS.get(contenttype)
    if not cls:
        # just use the major part of mimetype
        cls = contenttype.split("/", 1)[0]
    return f"moin-mime-{cls}"


def utctimestamp(dt):
    """
    convert a datetime object (UTC) to a UNIX timestamp (UTC)

    Note: time library writers seem to have a distorted relationship to inverse
          functions and also to UTC (see time.gmtime, see datetime.utcfromtimestamp).
    """
    from calendar import timegm

    return timegm(dt.timetuple())


def shorten_ctype(contenttype):
    """
    Returns user understandable terms for contenttype.

    :param contenttype: contains the long form of the contenttype
    :rtype: unicode
    :returns: user understandable version of contenttype
    """
    return CONTENTTYPES_MAP.get(contenttype, "Unknown")


def time_hh_mm(dt):
    """
    Convert a datetime object or timestamp into a short string of the form HH:MM
    where HH varies from 0 to 23.
    """
    return show_time.format_time(dt, fmt="HH:mm")


def time_datetime(dt):
    """
    Alternative to babel datetimeformat, allows user to choose ISO 8601 format
    by checking box in usersettings Options. Input may be datetime object or
    timestamp.
    """
    return show_time.format_date_time(dt)


def setup_jinja_env():
    app.jinja_env.filters["shorten_fqname"] = shorten_fqname
    app.jinja_env.filters["shorten_item_name"] = shorten_item_name
    app.jinja_env.filters["shorten_id"] = shorten_id
    app.jinja_env.filters["contenttype_to_class"] = contenttype_to_class
    app.jinja_env.filters["json_dumps"] = dumps
    app.jinja_env.filters["shorten_ctype"] = shorten_ctype
    app.jinja_env.filters["time_hh_mm"] = time_hh_mm
    app.jinja_env.filters["time_datetime"] = time_datetime
    # please note that these filters are installed by flask-babel:
    # datetimeformat, dateformat, timeformat, timedeltaformat

    app.jinja_env.globals.update(
        {
            # please note that flask-babel/jinja2.ext installs:
            # _, gettext, ngettext
            "isinstance": isinstance,
            "list": list,
            "Type": Type,
            # please note that flask-theme installs:
            # theme, theme_static
            "theme_supp": ThemeSupport(app.cfg),
            "user": flaskg.user,
            "storage": flaskg.storage,
            "clock": flaskg.clock,
            "cfg": app.cfg,
            "item_name": request.view_args.get("item_name", ""),
            "url_for_item": url_for_item,
            "get_fqname": get_fqname,
            "get_editor_info": lambda meta: get_editor_info(meta),
            "get_assigned_to_info": lambda meta: get_assigned_to_info(meta),
            "utctimestamp": lambda dt: utctimestamp(dt),
            "gen": make_generator(),
            "search_form": SearchForm.from_defaults(),
        }
    )

    # if Jinja whitespace control options are turned on, it becomes obvious why the default is off
    # app.jinja_env.trim_blocks = True
    # app.jinja_env.lstrip_blocks = True
