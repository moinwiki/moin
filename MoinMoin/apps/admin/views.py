"""
    MoinMoin - admin views

    This shows the user interface for wiki admins.

    @copyright: 2008-2010 MoinMoin:ThomasWaldmann,
                2001-2003 Juergen Hermann <jh@web.de>,
                2010 MoinMoin:DiogenesAugusto,
                2010 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

from flask import request, url_for, flash, redirect
from flask import current_app as app
from flask import flaskg

from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template
from MoinMoin.apps.admin import admin
from MoinMoin import user

@admin.route('/')
def index():
    return render_template('admin/index.html', item_name="+admin")


@admin.route('/userbrowser')
def userbrowser():
    """
    User Account Browser
    """
    # XXX add superuser check
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
    # XXX add superuser check
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
        except BackendError, e:
            flash(_('System items upgrade failed due to the following error: %(error)s.', error=e), 'error')
        else:
            flash(_('System items have been upgraded successfully!'))
        return redirect(url_for('admin.index'))

