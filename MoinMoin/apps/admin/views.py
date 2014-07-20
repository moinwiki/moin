# Copyright: 2007-2011 MoinMoin:ThomasWaldmann
# Copyright: 2001-2003 Juergen Hermann <jh@web.de>
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2009 MoinMoin:EugeneSyromyatnikov
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2010 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - admin views

This shows the user interface for wiki admins.
"""
from collections import namedtuple
from flask import request, url_for, flash, redirect
from flask import current_app as app
from flask import g as flaskg
from whoosh.query import Term, And
from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template, get_editor_info
from MoinMoin.apps.admin import admin
from MoinMoin import user
from MoinMoin.constants.keys import NAME, ITEMID, SIZE, EMAIL, DISABLED, NAME_EXACT, WIKINAME, TRASH, NAMESPACE, NAME_OLD, REVID, MTIME, COMMENT, LATEST_REVS, EMAIL_UNVALIDATED, ACL
from MoinMoin.constants.namespaces import NAMESPACE_USERPROFILES, NAMESPACE_DEFAULT, NAMESPACE_ALL
from MoinMoin.constants.rights import SUPERUSER, ACL_RIGHTS_CONTENTS
from MoinMoin.security import require_permission, ACLStringIterator
from MoinMoin.util.interwiki import CompositeName
from MoinMoin.datastruct.backends.wiki_groups import WikiGroup
from MoinMoin.datastruct.backends import GroupDoesNotExistError


@admin.route('/superuser')
@require_permission(SUPERUSER)
def index():
    return render_template('admin/index.html', title_name=_(u"Admin"))


@admin.route('/user')
def index_user():
    return render_template('user/index_user.html', title_name=_(u"User"))


@admin.route('/userbrowser')
@require_permission(SUPERUSER)
def userbrowser():
    """
    User Account Browser
    """
    groups = flaskg.groups
    revs = user.search_users()  # all users
    user_accounts = []
    for rev in revs:
        user_groups = []
        user_names = rev.meta[NAME]
        for groupname in groups:
            group = groups[groupname]
            for name in user_names:
                if name in group:
                    user_groups.append(groupname)
        user_accounts.append(dict(uid=rev.meta[ITEMID],
                                  name=user_names,
                                  fqname=CompositeName(NAMESPACE_USERPROFILES, NAME_EXACT, rev.name),
                                  email=rev.meta[EMAIL] if EMAIL in rev.meta else rev.meta[EMAIL_UNVALIDATED],
                                  disabled=rev.meta[DISABLED],
                                  groups=user_groups))
    return render_template('admin/userbrowser.html', user_accounts=user_accounts, title_name=_(u"Users"))


@admin.route('/userprofile/<user_name>', methods=['GET', 'POST', ])
@require_permission(SUPERUSER)
def userprofile(user_name):
    """
    Set values in user profile
    """
    u = user.User(auth_username=user_name)
    if request.method == 'GET':
        return _(u"User profile of %(username)s: %(email)s %(disabled)s", username=user_name,
                 email=u.email, disabled=u.disabled)

    if request.method == 'POST':
        key = request.form.get('key', '')
        val = request.form.get('val', '')
        ok = False
        if hasattr(u, key):
            ok = True
            oldval = u.profile[key]
            if isinstance(oldval, bool):
                val = bool(int(val))
            elif isinstance(oldval, int):
                val = int(val)
            elif isinstance(oldval, unicode):
                val = unicode(val)
            else:
                ok = False
        if ok:
            u.profile[key] = val
            u.save()
            flash(u'{0}.{1}: {2} -> {3}'.format(user_name, key, unicode(oldval), unicode(val), ), "info")
        else:
            flash(u'modifying {0}.{1} failed'.format(user_name, key, ), "error")
    return redirect(url_for('.userbrowser'))


@admin.route('/mail_recovery_token', methods=['GET', 'POST', ])
def mail_recovery_token():
    """
    Send user an email so he can reset his password.
    """
    flash("mail recovery token not implemented yet")
    return redirect(url_for('.userbrowser'))


from MoinMoin.config import default as defaultconfig


@admin.route('/wikiconfig', methods=['GET', ])
@require_permission(SUPERUSER)
def wikiconfig():
    settings = {}
    for groupname in defaultconfig.options:
        heading, desc, opts = defaultconfig.options[groupname]
        for name, default, description in opts:
            name = groupname + '_' + name
            if isinstance(default, defaultconfig.DefaultExpression):
                default = default.value
            settings[name] = default
    for groupname in defaultconfig.options_no_group_name:
        heading, desc, opts = defaultconfig.options_no_group_name[groupname]
        for name, default, description in opts:
            if isinstance(default, defaultconfig.DefaultExpression):
                default = default.value
            settings[name] = default

    def iter_vnames(cfg):
        dedup = {}
        for name in cfg.__dict__:
            dedup[name] = True
            yield name, cfg.__dict__[name]
        for cls in cfg.__class__.mro():
            if cls == defaultconfig.ConfigFunctionality:
                break
            for name in cls.__dict__:
                if name not in dedup:
                    dedup[name] = True
                    yield name, cls.__dict__[name]

    found = []
    for vname, value in iter_vnames(app.cfg):
        if hasattr(defaultconfig.ConfigFunctionality, vname):
            continue
        if vname in settings and settings[vname] == value:
            continue
        found.append((vname, value))

    found.sort()
    return render_template('admin/wikiconfig.html',
                           title_name=_(u"Show Wiki Configuration"),
                           found=found, settings=settings)


@admin.route('/wikiconfighelp', methods=['GET', ])
@require_permission(SUPERUSER)
def wikiconfighelp():
    def format_default(default):
        if isinstance(default, defaultconfig.DefaultExpression):
            default_txt = default.text
        else:
            default_txt = repr(default)
            if len(default_txt) > 30:
                default_txt = '...'
        return default_txt

    groups = []
    for groupname in defaultconfig.options:
        heading, desc, opts = defaultconfig.options[groupname]
        opts = sorted([(groupname + '_' + name, format_default(default), description)
                       for name, default, description in opts])
        groups.append((heading, desc, opts))
    for groupname in defaultconfig.options_no_group_name:
        heading, desc, opts = defaultconfig.options_no_group_name[groupname]
        opts = sorted([(name, format_default(default), description)
                       for name, default, description in opts])
        groups.append((heading, desc, opts))
    groups.sort()
    return render_template('admin/wikiconfighelp.html',
                           title_name=_(u"Wiki Configuration Help"),
                           groups=groups)


@admin.route('/highlighterhelp', methods=['GET', ])
def highlighterhelp():
    """display a table with list of available Pygments lexers"""
    import pygments.lexers
    headings = [
        _('Lexer description'),
        _('Lexer names'),
        _('File patterns'),
        _('Mimetypes'),
    ]
    lexers = pygments.lexers.get_all_lexers()
    rows = sorted([[desc, ' '.join(names), ' '.join(patterns), ' '.join(mimetypes), ]
                   for desc, names, patterns, mimetypes in lexers])
    return render_template('user/highlighterhelp.html',
                           title_name=_(u"Highlighters"),
                           headings=headings,
                           rows=rows)


@admin.route('/interwikihelp', methods=['GET', ])
def interwikihelp():
    """display a table with list of known interwiki names / urls"""
    headings = [
        _('InterWiki name'),
        _('URL'),
    ]
    rows = sorted(app.cfg.interwiki_map.items())
    return render_template('user/interwikihelp.html',
                           title_name=_(u"Interwiki Names"),
                           headings=headings,
                           rows=rows)


@admin.route('/itemsize', methods=['GET', ])
def itemsize():
    """display a table with item sizes"""
    headings = [
        _('Size'),
        _('Item name'),
    ]
    rows = [(rev.meta[SIZE], rev.name)
            for rev in flaskg.storage.documents(wikiname=app.cfg.interwikiname)]
    rows = sorted(rows, reverse=True)
    return render_template('user/itemsize.html',
                           title_name=_(u"Item Sizes"),
                           headings=headings,
                           rows=rows)


@admin.route('/trash', defaults=dict(namespace=NAMESPACE_DEFAULT), methods=['GET'])
@admin.route('/<namespace>/trash')
def trash(namespace):
    """
    Returns the trashed items.
    """
    trash = _trashed(namespace)
    return render_template('admin/trash.html',
                           headline=_(u'Trashed Items'),
                           title_name=_(u'Trashed Items'),
                           results=trash)


def _trashed(namespace):
    q = And([Term(WIKINAME, app.cfg.interwikiname), Term(TRASH, True)])
    if not namespace == NAMESPACE_ALL:
        q = And([q, Term(NAMESPACE, namespace), ])
    trashedEntry = namedtuple('trashedEntry', 'fqname oldname revid mtime comment editor')
    results = []
    for rev in flaskg.storage.search(q, limit=None):
        meta = rev.meta
        results.append(trashedEntry(rev.fqname, meta[NAME_OLD], meta[REVID], meta[MTIME], meta[COMMENT], get_editor_info(meta)))
    return results


@admin.route('/user_acl_report/<uid>', methods=['GET'])
@require_permission(SUPERUSER)
def user_acl_report(uid):
    all_items = flaskg.storage.documents(wikiname=app.cfg.interwikiname)
    groups = flaskg.groups
    theuser = user.User(uid=uid)
    itemwise_acl = []
    for item in all_items:
        fqname = CompositeName(item.meta.get(NAMESPACE), u'itemid', item.meta.get(ITEMID))
        itemwise_acl.append({'name': item.meta.get(NAME),
                             'itemid': item.meta.get(ITEMID),
                             'fqname': fqname,
                             'read': theuser.may.read(fqname),
                             'write': theuser.may.write(fqname),
                             'create': theuser.may.create(fqname),
                             'admin': theuser.may.admin(fqname),
                             'destroy': theuser.may.destroy(fqname)})
    return render_template('admin/user_acl_report.html',
                           title_name=_(u'User ACL Report'),
                           user_names=theuser.name,
                           itemwise_acl=itemwise_acl)


@admin.route('/groupbrowser', methods=['GET'])
@require_permission(SUPERUSER)
def groupbrowser():
    """
    Display list of all groups and their members
    """
    all_groups = flaskg.groups
    groups = []
    for group in all_groups:
        group_type = ''
        if isinstance(all_groups[group], WikiGroup):
            group_type = 'WikiGroup'
        else:
            group_type = 'ConfigGroup'
        groups.append(dict(name=all_groups[group].name,
                           member_users=all_groups[group].members,
                           member_groups=all_groups[group].member_groups,
                           grouptype=group_type))
    return render_template('admin/groupbrowser.html',
                           title_name=_(u'Groups'),
                           groups=groups)


@admin.route('/item_acl_report', methods=['GET'])
@require_permission(SUPERUSER)
def item_acl_report():
    """
    Return a list of all items in the wiki along with the ACL Meta-data
    """
    all_items = flaskg.storage.documents(wikiname=app.cfg.interwikiname)
    items_acls = []
    for item in all_items:
        item_namespace = item.meta.get(NAMESPACE)
        item_id = item.meta.get(ITEMID)
        item_name = item.meta.get(NAME)
        item_acl = item.meta.get(ACL)
        fqname = CompositeName(item_namespace, u'itemid', item_id)
        if item_acl is None:
            for namespace, acl_config in app.cfg.acl_mapping:
                if item_namespace == namespace or item_namespace == 'userprofiles' and namespace == 'userprofiles/':
                    item_acl = 'Default ({0})'.format(acl_config['default'])
        items_acls.append({'name': item_name,
                           'itemid': item_id,
                           'fqname': fqname,
                           'acl': item_acl})
    return render_template('admin/item_acl_report.html',
                           title_name=_('Item ACL Report'),
                           items_acls=items_acls)


def search_group(group_name):
    groups = flaskg.groups
    if groups[group_name]:
            return groups[group_name]
    else:
        raise GroupDoesNotExistError(group_name)


@admin.route('/group_acl_report/<group_name>')
@require_permission(SUPERUSER)
def group_acl_report(group_name):
    """
    Display a 2-column table of items and ACLs, where the ACL rule specifies any
    WikiGroup or ConfigGroup name.
    """
    group = search_group(group_name)
    all_items = flaskg.storage.documents(wikiname=app.cfg.interwikiname)
    group_items = []
    for item in all_items:
        acl_iterator = ACLStringIterator(ACL_RIGHTS_CONTENTS, item.meta.get(ACL, ''))
        for modifier, entries, rights in acl_iterator:
            if group_name in entries:
                item_id = item.meta.get(ITEMID)
                fqname = CompositeName(item.meta.get(NAMESPACE), u'itemid', item_id)
                group_items.append(dict(name=item.meta.get(NAME),
                                        itemid=item_id,
                                        fqname=fqname,
                                        rights=rights))
    return render_template('admin/group_acl_report.html',
                           title_name=_(u'Group ACL Report'),
                           group_items=group_items,
                           group_name=group_name)
