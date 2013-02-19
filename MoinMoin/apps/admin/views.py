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

from flask import request, url_for, flash, redirect
from flask import current_app as app
from flask import g as flaskg

from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template
from MoinMoin.apps.admin import admin
from MoinMoin import user
from MoinMoin.constants.keys import NAME, ITEMID, SIZE, EMAIL
from MoinMoin.constants.rights import SUPERUSER
from MoinMoin.security import require_permission


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
    user_accounts = [dict(uid=rev.meta[ITEMID],
                          name=rev.meta[NAME],
                          email=rev.meta[EMAIL],
                          disabled=False,  # TODO: add to index
                          groups=[groupname for groupname in groups if rev.meta[NAME] in groups[groupname]],
                     ) for rev in revs]
    return render_template('admin/userbrowser.html', user_accounts=user_accounts, title_name=_(u"Users"))


@admin.route('/userprofile/<user_name>', methods=['GET', 'POST', ])
@require_permission(SUPERUSER)
def userprofile(user_name):
    """
    Set values in user profile
    """
    u = user.User(auth_username=user_name)
    if request.method == 'GET':
        return _(u"User profile of %(username)s: %(email)r", username=user_name,
                 email=(u.email, u.disabled))

    if request.method == 'POST':
        key = request.form.get('key', '')
        val = request.form.get('val', '')
        ok = False
        if hasattr(u, key):
            ok = True
            oldval = getattr(u, key)
            if isinstance(oldval, bool):
                val = bool(val)
            elif isinstance(oldval, int):
                val = int(val)
            elif isinstance(oldval, unicode):
                val = unicode(val)
            else:
                ok = False
        if ok:
            setattr(u, key, val)
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


@admin.route('/sysitems_upgrade', methods=['GET', 'POST', ])
@require_permission(SUPERUSER)
def sysitems_upgrade():
    from MoinMoin.storage.backends import upgrade_sysitems  # XXX broken import, either fix or kill this
    from MoinMoin.storage.error import BackendError
    if request.method == 'GET':
        action = 'syspages_upgrade'
        label = 'Upgrade System Pages'
        return render_template('admin/sysitems_upgrade.html',
                               title_name=_(u"System items upgrade"))
    if request.method == 'POST':
        xmlfile = request.files.get('xmlfile')
        try:
            upgrade_sysitems(xmlfile)
        except BackendError as e:
            flash(_('System items upgrade failed due to the following error: %(error)s.', error=e), 'error')
        else:
            flash(_('System items have been upgraded successfully!'))
        return redirect(url_for('.index'))


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
                if not name in dedup:
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
