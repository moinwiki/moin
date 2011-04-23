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


from flask import request, url_for, flash, redirect, abort
from flask import current_app as app
from flask import g as flaskg

from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template
from MoinMoin.apps.admin import admin
from MoinMoin import user
from MoinMoin.storage.error import NoSuchRevisionError
from MoinMoin.config import SIZE

@admin.route('/')
def index():
    return render_template('admin/index.html', item_name="+admin")


@admin.route('/userbrowser')
def userbrowser():
    """
    User Account Browser
    """
    if not flaskg.user.may.superuser():
        abort(403)

    groups = flaskg.groups
    user_accounts = []
    for uid in user.getUserList():
        u = user.User(uid)
        user_accounts.append(dict(
            uid=uid,
            name=u.name,
            email=u.email,
            disabled=u.disabled,
            groups=[groupname for groupname in groups if u.name in groups[groupname]],
            ))
    return render_template('admin/userbrowser.html', user_accounts=user_accounts, item_name="+admin/Userbrowser")


@admin.route('/userprofile/<user_name>', methods=['GET', 'POST', ])
def userprofile(user_name):
    """
    Set values in user profile
    """
    if not flaskg.user.may.superuser():
        abort(403)

    uid = user.getUserId(user_name)
    u = user.User(uid)
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
            theuser.save()
            flash('%s.%s: %s -> %s' % (user_name, key, unicode(oldval), unicode(val), ), "info")
        else:
            flash('modifying %s.%s failed' % (user_name, key, ), "error")
    return redirect(url_for('admin.userbrowser'))


@admin.route('/mail_recovery_token', methods=['GET', 'POST', ])
def mail_recovery_token():
    """
    Send user an email so he can reset his password.
    """
    flash("mail recovery token not implemented yet")
    return redirect(url_for('admin.userbrowser'))


@admin.route('/sysitems_upgrade', methods=['GET', 'POST', ])
def sysitems_upgrade():
    if not flaskg.user.may.superuser():
        abort(403)

    from MoinMoin.storage.backends import upgrade_sysitems
    from MoinMoin.storage.error import BackendError
    if request.method == 'GET':
        action = 'syspages_upgrade'
        label = 'Upgrade System Pages'
        return render_template('admin/sysitems_upgrade.html',
                               item_name="+admin/System items upgrade")
    if request.method == 'POST':
        xmlfile = request.files.get('xmlfile')
        try:
            upgrade_sysitems(xmlfile)
        except BackendError as e:
            flash(_('System items upgrade failed due to the following error: %(error)s.', error=e), 'error')
        else:
            flash(_('System items have been upgraded successfully!'))
        return redirect(url_for('admin.index'))


from MoinMoin.config import default as defaultconfig

@admin.route('/wikiconfig', methods=['GET', ])
def wikiconfig():
    if not flaskg.user.may.superuser():
        abort(403)

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
                           item_name="+admin/wikiconfig",
                           found=found, settings=settings)


@admin.route('/wikiconfighelp', methods=['GET', ])
def wikiconfighelp():
    if not flaskg.user.may.superuser():
        abort(403)

    def format_default(default):
        if isinstance(default, defaultconfig.DefaultExpression):
            default_txt = default.text
        else:
            default_txt = '%r' % (default, )
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
                           item_name="+admin/wikiconfighelp",
                           groups=groups)


@admin.route('/highlighterhelp', methods=['GET', ])
def highlighterhelp():
    """display a table with list of available Pygments lexers"""
    import pygments.lexers
    headings = [_('Lexer description'),
                _('Lexer names'),
                _('File patterns'),
                _('Mimetypes'),
               ]
    lexers = pygments.lexers.get_all_lexers()
    rows = sorted([[desc, ' '.join(names), ' '.join(patterns), ' '.join(mimetypes), ]
                   for desc, names, patterns, mimetypes in lexers])
    return render_template('admin/highlighterhelp.html',
                           item_name="+admin/highlighterhelp",
                           headings=headings,
                           rows=rows)


@admin.route('/interwikihelp', methods=['GET', ])
def interwikihelp():
    """display a table with list of known interwiki names / urls"""
    headings = [_('InterWiki name'),
                _('URL'),
               ]
    rows = sorted(app.cfg.interwiki_map.items())
    return render_template('admin/interwikihelp.html',
                           item_name="+admin/interwikihelp",
                           headings=headings,
                           rows=rows)


@admin.route('/itemsize', methods=['GET', ])
def itemsize():
    """display a table with item sizes"""
    headings = [_('Size'),
                _('Item name'),
               ]
    rows = []
    for item in flaskg.storage.iteritems():
        try:
            rev = item.get_revision(-1)
        except NoSuchRevisionError:
            # XXX we currently also get user items, they have no revisions -
            # but in the end, they should not be readable by the user anyways
            continue
        rows.append((rev[SIZE], item.name))
    rows = sorted(rows, reverse=True)
    return render_template('admin/itemsize.html',
                           item_name="+admin/itemsize",
                           headings=headings,
                           rows=rows)


