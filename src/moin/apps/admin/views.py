# Copyright: 2007-2011 MoinMoin:ThomasWaldmann
# Copyright: 2001-2003 Juergen Hermann <jh@web.de>
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2009 MoinMoin:EugeneSyromyatnikov
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2010 MoinMoin:ReimarBauer
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - admin views

This shows the user interface for wiki admins.
"""
from collections import namedtuple

from flask import request, url_for, flash, redirect
from flask import Response
from flask import current_app as app
from flask import g as flaskg

from flatland.validation import Validator
from flatland import Form

from whoosh.query import Term, And, Not

from moin.i18n import _, L_
from moin.themes import render_template, get_editor_info
from moin.apps.admin import admin
from moin.apps.frontend.views import _using_moin_auth
from moin import user
from moin.constants.keys import (
    NAME,
    DISPLAY_NAME,
    ITEMID,
    SIZE,
    EMAIL,
    DISABLED,
    NAME_EXACT,
    WIKINAME,
    TRASH,
    NAMESPACE,
    NAME_OLD,
    REVID,
    REV_NUMBER,
    MTIME,
    COMMENT,
    LATEST_REVS,
    EMAIL_UNVALIDATED,
    ACL,
    ACTION,
    ACTION_SAVE,
    SUBSCRIPTIONS,
    PARENTID,
)
from moin.constants.namespaces import NAMESPACE_USERPROFILES, NAMESPACE_USERS, NAMESPACE_DEFAULT, NAMESPACE_ALL
from moin.constants.rights import SUPERUSER, ACL_RIGHTS_CONTENTS, READ, WRITE, CREATE, ADMIN, DESTROY
from moin.security import require_permission, ACLStringIterator
from moin.storage.middleware.protecting import AccessDenied, gen_fqnames
from moin.storage.middleware.indexing import parent_names
from moin.utils.interwiki import CompositeName
from moin.utils.crypto import make_uuid
from moin.datastructures.backends.wiki_groups import WikiGroup
from moin.datastructures.backends import GroupDoesNotExistError
from moin.items import Item, acl_validate
from moin.utils.interwiki import split_fqname
from moin.config import default as defaultconfig
from moin.forms import RequiredText, YourEmail


@admin.route("/superuser")
@require_permission(SUPERUSER)
def index():
    return render_template("admin/index.html", title_name=_("Admin"))


@admin.route("/user")
def index_user():
    return render_template(
        "user/index_user.html",
        title_name=_("User"),
        flaskg=flaskg,
        NAMESPACE_USERPROFILES=NAMESPACE_USERPROFILES,
        app=app,
    )


class ValidRegisterNewUser(Validator):
    """
    Validator for RegisterNewUserForm.
    """

    def validate(self, element, state):
        if not (element["username"].valid and element["email"].valid):
            return False
        return True


class RegisterNewUserForm(Form):
    """
    Simple user registration form for use by SuperUsers to create new accounts.
    """

    name = "register_new_user"
    username = RequiredText.using(label=L_("Username")).with_properties(placeholder=L_("User Name"), autofocus=True)
    email = YourEmail
    submit_label = L_("Register")
    validators = [ValidRegisterNewUser()]


@admin.route("/register_new_user", methods=["GET", "POST"])
@require_permission(SUPERUSER)
def register_new_user():
    """
    Create a new account and send email with link to create password.
    """
    if not _using_moin_auth():
        return Response("No MoinAuth in auth list", 403)

    title_name = _("Register New User")
    FormClass = RegisterNewUserForm

    if request.method in ["GET", "HEAD"]:
        form = FormClass.from_defaults()
    elif request.method == "POST":
        form = FormClass.from_flat(request.form)
        if form.validate():
            username = form["username"].value
            email = form["email"].value
            user_profile = user.UserProfile()
            user_profile[ITEMID] = make_uuid()
            user_profile[NAME] = [username]
            user_profile[EMAIL] = email
            user_profile[DISABLED] = False
            user_profile[ACTION] = ACTION_SAVE

            users = user.search_users(**{NAME_EXACT: username})
            if users:
                flash(_("User already exists"), "error")
            emails = None
            if app.cfg.user_email_unique:
                emails = user.search_users(email=email)
                if emails:
                    flash(_("This email already belongs to somebody else."), "error")
            if not (users or emails):
                user_profile.save()
                flash(_("Account for {username} created").format(username=username), "info")
                form = FormClass.from_defaults()

                u = user.User(auth_username=username)
                if u.valid:
                    is_ok, msg = u.mail_password_recovery()
                    if not is_ok:
                        flash(msg, "error")
                    else:
                        flash(
                            L_("{username} has been sent a password recovery email.").format(username=username), "info"
                        )
                else:
                    flash(
                        _("{username} is an invalid user, no email has been sent.").format(username=username), "error"
                    )

    return render_template("admin/register_new_user.html", title_name=title_name, form=form)


@admin.route("/userbrowser")
@require_permission(SUPERUSER)
def userbrowser():
    """
    User Account Browser
    """
    groups = flaskg.groups
    member_groups = {}  # {username: [list of groups], ...}
    for groupname in groups:
        group = groups[groupname]
        for member in group.members:
            member_groups[member] = member_groups.get(member, []) + [group.name]

    revs = user.search_users()  # all users
    user_accounts = []
    for rev in revs:
        user_names = rev.meta[NAME]
        display_name = rev.meta.get(DISPLAY_NAME, "")
        user_groups = member_groups.get(user_names[0], [])
        for name in user_names[1:]:
            user_groups = user_groups + member_groups.get(name, [])
        subscriptions = rev.meta[SUBSCRIPTIONS]
        user_accounts.append(
            dict(
                uid=rev.meta[ITEMID],
                name=user_names,
                display_name=display_name,
                fqname=CompositeName(NAMESPACE_USERS, NAME_EXACT, rev.name),
                email=rev.meta[EMAIL] if EMAIL in rev.meta else rev.meta[EMAIL_UNVALIDATED],
                disabled=rev.meta[DISABLED],
                groups=user_groups,
                subscriptions=subscriptions,
            )
        )
    return render_template("admin/userbrowser.html", user_accounts=user_accounts, title_name=_("Users"))


@admin.route("/userprofile/<user_name>", methods=["GET", "POST"])
@require_permission(SUPERUSER)
def userprofile(user_name):
    """
    Set values in user profile
    """
    u = user.User(auth_username=user_name)
    if request.method == "GET":
        return _("User profile of {username}: {email} {disabled}").format(
            username=user_name, email=u.email, disabled=u.disabled
        )

    if request.method == "POST":
        key = request.form.get("key", "")
        val = request.form.get("val", "")
        ok = False
        if hasattr(u, key):
            ok = True
            oldval = u.profile[key]
            if isinstance(oldval, bool):
                val = bool(int(val))
            elif isinstance(oldval, int):
                val = int(val)
            elif isinstance(oldval, str):
                val = str(val)
            else:
                ok = False
        if ok:
            u.profile[key] = val
            u.save()
            flash(_('{0} "{1}" status changed to "{2}"').format(user_name, key, str(val)), "info")
        else:
            flash(_("modifying {0}.{1} failed").format(user_name, key), "error")
    return redirect(url_for(".userbrowser"))


@admin.route("/mail_recovery_token", methods=["GET", "POST"])
@require_permission(SUPERUSER)
def mail_recovery_token():
    """
    Send user an email so he can reset his password.
    """
    username = request.form.get("username", "")
    if username:
        u = user.User(auth_username=username)
        if u.valid:
            is_ok, msg = u.mail_password_recovery()
            if not is_ok:
                flash(msg, "error")
            else:
                flash(_("{0} has been sent a password recovery email.").format(username), "info")
        else:
            flash(_("{0} is an invalid user, no email has been sent.").format(username), "error")
    else:
        flash(_("No user name provided, no email sent."), "error")
    return redirect(url_for(".userbrowser"))


@admin.route("/wikiconfig", methods=["GET"])
@require_permission(SUPERUSER)
def wikiconfig():
    settings = {}
    for groupname in defaultconfig.options:
        heading, desc, opts = defaultconfig.options[groupname]
        for name, default, description in opts:
            name = groupname + "_" + name
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
    found_default = []
    for vname, value in iter_vnames(app.cfg):
        if hasattr(defaultconfig.ConfigFunctionality, vname):
            continue
        if vname in settings and settings[vname] == value:
            found_default.append((vname, value))
            continue
        found.append((vname, value))

    found.sort()
    found_default.sort()
    return render_template(
        "admin/wikiconfig.html",
        title_name=_("Show Wiki Configuration"),
        len=len,
        found=found,
        found_default=found_default,
        settings=settings,
    )


@admin.route("/wikiconfighelp", methods=["GET"])
@require_permission(SUPERUSER)
def wikiconfighelp():
    max_len_default = 60

    def format_default(default):
        if isinstance(default, defaultconfig.DefaultExpression):
            default_txt = default.text
        else:
            if len(repr(default)) > max_len_default and isinstance(default, list) and len(default) > 1:
                txt = ["["]
                for entry in default:
                    txt.append(f"&#013;{repr(entry)},")
                txt.append("&#013;]")
                return "".join(txt)
            elif len(repr(default)) > max_len_default and isinstance(default, dict) and len(default) > 1:
                txt = ["{"]
                for key, val in default.items():
                    txt.append(f"&#013;{repr(key)}: {repr(val)},")
                txt.append("&#013;}")
                return "".join(txt)
            else:
                default_txt = repr(default)
        return default_txt

    groups = []
    for groupname in defaultconfig.options:
        heading, desc, opts = defaultconfig.options[groupname]
        opts = sorted(
            [(groupname + "_" + name, format_default(default), description) for name, default, description in opts]
        )
        groups.append((heading, desc, opts))
    for groupname in defaultconfig.options_no_group_name:
        heading, desc, opts = defaultconfig.options_no_group_name[groupname]
        opts = sorted([(name, format_default(default), description) for name, default, description in opts])
        groups.append((heading, desc, opts))
    groups.sort()
    return render_template(
        "admin/wikiconfighelp.html",
        title_name=_("Wiki Configuration Help"),
        groups=groups,
        len=len,
        max_len_default=max_len_default,
    )


@admin.route("/highlighterhelp", methods=["GET"])
def highlighterhelp():
    """display a table with list of available Pygments lexers"""
    import pygments.lexers

    headings = [_("Lexer description"), _("Lexer names"), _("File patterns"), _("Mimetypes")]
    lexers = pygments.lexers.get_all_lexers()
    rows = sorted(
        [
            [desc, " ".join(names), " ".join(patterns), " ".join(mimetypes)]
            for desc, names, patterns, mimetypes in lexers
        ]
    )
    return render_template("user/highlighterhelp.html", title_name=_("Highlighters"), headings=headings, rows=rows)


@admin.route("/interwikihelp", methods=["GET"])
def interwikihelp():
    """display a table with list of known interwiki names / urls"""
    headings = [_("InterWiki name"), _("URL")]
    rows = sorted(app.cfg.interwiki_map.items())
    return render_template("user/interwikihelp.html", title_name=_("Interwiki Names"), headings=headings, rows=rows)


@admin.route("/itemsize", methods=["GET"])
def itemsize():
    """display a table with item sizes"""
    headings = [_("Size"), _("Item name")]
    query = And(
        [Term(WIKINAME, app.cfg.interwikiname), Not(Term(NAMESPACE, NAMESPACE_USERPROFILES)), Not(Term(TRASH, True))]
    )
    revs = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, sortedby=[NAME], limit=None)
    rows = [(rev[SIZE], CompositeName(rev[NAMESPACE], NAME_EXACT, rev[NAME][0])) for rev in revs]
    rows = sorted(rows, reverse=True)
    return render_template("user/itemsize.html", title_name=_("Item Sizes"), headings=headings, rows=rows)


@admin.route("/trash", defaults=dict(namespace=NAMESPACE_DEFAULT), methods=["GET"])
@admin.route("/<namespace>/trash")
@require_permission(SUPERUSER)
def trash(namespace):
    """
    Returns the trashed items.
    """
    trash = _trashed(namespace)
    return render_template(
        "admin/trash.html", headline=_("Trashed Items"), title_name=_("Trashed Items"), results=trash
    )


def _trashed(namespace):
    q = And([Term(WIKINAME, app.cfg.interwikiname), Term(TRASH, True)])
    if namespace != NAMESPACE_ALL:
        q = And([q, Term(NAMESPACE, namespace)])
    trashedEntry = namedtuple("trashedEntry", "fqname oldname revid rev_number mtime comment editor parentid")
    results = []
    for meta in flaskg.storage.search_meta(q, limit=None):
        fqname = CompositeName(meta[NAMESPACE], ITEMID, meta[ITEMID])
        results.append(
            trashedEntry(
                fqname,
                meta[NAME_OLD],
                meta[REVID],
                meta[REV_NUMBER],
                meta[MTIME],
                meta[COMMENT],
                get_editor_info(meta),
                meta[PARENTID],
            )
        )
    return results


@admin.route("/user_acl_report/<uid>", methods=["GET"])
@require_permission(SUPERUSER)
def user_acl_report(uid):
    query = And([Term(WIKINAME, app.cfg.interwikiname), Not(Term(NAMESPACE, NAMESPACE_USERPROFILES))])
    all_metas = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, sortedby=[NAMESPACE, NAME], limit=None)
    theuser = user.User(uid=uid)
    itemwise_acl = []
    for meta in all_metas:
        fqname = gen_fqnames(meta)
        acl_parts = {
            "name": meta.get(NAME),
            "namespace": meta.get(NAMESPACE),
            "itemid": meta.get(ITEMID),
            "fqname": fqname,
        }
        parentnames = tuple(parent_names(meta[NAME]))
        usernames = tuple(theuser.name)
        acl = meta.get(ACL, None)
        last_item_result = {
            "read": flaskg.storage.allows(usernames, acl, parentnames, meta[NAMESPACE], READ),
            "write": flaskg.storage.allows(usernames, acl, parentnames, meta[NAMESPACE], WRITE),
            "create": flaskg.storage.allows(usernames, acl, parentnames, meta[NAMESPACE], CREATE),
            "admin": flaskg.storage.allows(usernames, acl, parentnames, meta[NAMESPACE], ADMIN),
            "destroy": flaskg.storage.allows(usernames, acl, parentnames, meta[NAMESPACE], DESTROY),
        }
        itemwise_acl.append({**acl_parts, **last_item_result})
    return render_template(
        "admin/user_acl_report.html",
        title_name=_("User ACL Report"),
        user_names=theuser.name,
        itemwise_acl=itemwise_acl,
    )


@admin.route("/groupbrowser", methods=["GET"])
@require_permission(SUPERUSER)
def groupbrowser():
    """
    Display list of all groups and their members
    """
    all_groups = flaskg.groups
    groups = []
    for group in all_groups:
        group_type = ""
        if isinstance(all_groups[group], WikiGroup):
            group_type = "WikiGroup"
        else:
            group_type = "ConfigGroup"
        groups.append(
            dict(
                name=all_groups[group].name,
                member_users=all_groups[group].members,
                member_groups=all_groups[group].member_groups,
                grouptype=group_type,
            )
        )
    return render_template("admin/groupbrowser.html", title_name=_("Groups"), groups=groups)


@admin.route("/item_acl_report", methods=["GET"])
@require_permission(SUPERUSER)
def item_acl_report():
    """
    Return a sorted list of all items in the wiki along with the ACL Meta-data.

    Item names are prefixed with the namespace, if there is a non-default namespace.
    If there are multiple names, the first name is used for sorting.
    """
    query = And([Term(WIKINAME, app.cfg.interwikiname), Not(Term(NAMESPACE, NAMESPACE_USERPROFILES))])
    all_metas = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, sortedby=[NAMESPACE, NAME], limit=None)
    items_acls = []
    for meta in all_metas:
        item_namespace = meta.get(NAMESPACE)
        item_id = meta.get(ITEMID)
        if item_namespace:
            item_name = [item_namespace + "/" + name for name in meta.get(NAME)]
        else:
            item_name = meta.get(NAME)
        item_acl = meta.get(ACL)
        acl_default = item_acl is None
        if acl_default:
            for namespace, acl_config in app.cfg.acl_mapping:
                if item_namespace == namespace:
                    item_acl = acl_config["default"]
        fqnames = gen_fqnames(meta)
        items_acls.append(
            {
                "name": item_name,
                "name_old": meta.get("name_old", []),
                "itemid": item_id,
                "fqnames": fqnames,
                "fqname": fqnames[0],
                "acl": item_acl,
                "acl_default": acl_default,
            }
        )
    # deleted items have no names; this sort places deleted items on top of the report;
    # the display name may be similar to: "9cf939f ~(DeletedItemName)"
    items_acls = sorted(items_acls, key=lambda k: (k["name"], k["name_old"]))
    return render_template(
        "admin/item_acl_report.html",
        title_name=_("Item ACL Report"),
        number_items=len(items_acls),
        items_acls=items_acls,
    )


def search_group(group_name):
    groups = flaskg.groups
    if groups[group_name]:
        return groups[group_name]
    else:
        raise GroupDoesNotExistError(group_name)


@admin.route("/group_acl_report/<group_name>")
@require_permission(SUPERUSER)
def group_acl_report(group_name):
    """
    Display a table of items and permissions, where the ACL rule specifies any
    WikiGroup or ConfigGroup name.
    """
    query = And([Term(WIKINAME, app.cfg.interwikiname), Not(Term(NAMESPACE, NAMESPACE_USERPROFILES))])
    all_metas = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, sortedby=[NAMESPACE, NAME], limit=None)
    group_items = []
    for meta in all_metas:
        acl_iterator = ACLStringIterator(ACL_RIGHTS_CONTENTS, meta.get(ACL, ""))
        for modifier, entries, rights in acl_iterator:
            if group_name in entries:
                fqname = gen_fqnames(meta)
                group_items.append(
                    dict(
                        name=meta.get(NAME),
                        itemid=meta.get(ITEMID),
                        namespace=meta.get(NAMESPACE),
                        fqname=fqname,
                        rights=rights,
                    )
                )
    return render_template(
        "admin/group_acl_report.html", title_name=_("Group ACL Report"), group_items=group_items, group_name=group_name
    )


@admin.route("/modify_acl/<itemname:item_name>", methods=["POST"])
@require_permission(SUPERUSER)
def modify_acl(item_name):
    fqname = split_fqname(item_name)
    item = Item.create(item_name)
    meta = dict(item.meta)
    old_acl = meta.get(ACL, "")
    new_acl = request.form.get(fqname.fullname)
    is_valid = acl_validate(new_acl)
    if is_valid:
        if new_acl in ("Empty", ""):
            meta[ACL] = ""
        elif new_acl == "None" and ACL in meta:
            del meta[ACL]
        else:
            meta[ACL] = new_acl
        try:
            item._save(meta=meta)
        except AccessDenied:
            # superuser viewed item acl report and tried to change acl but lacked admin permission
            flash(
                L_("Failed! Not authorized.<br>Item: {item_name}<br>ACL: {acl_rule}").format(
                    item_name=fqname.fullname, acl_rule=old_acl
                ),
                "error",
            )
            return redirect(url_for(".item_acl_report"))
        flash(
            L_("Success! ACL saved.<br>Item: {item_name}<br>ACL: {acl_rule}").format(
                item_name=fqname.fullname, acl_rule=new_acl
            ),
            "info",
        )
    else:
        flash(
            L_("Nothing changed, invalid ACL.<br>Item: {item_name}<br>ACL: {acl_rule}").format(
                item_name=fqname.fullname, acl_rule=new_acl
            ),
            "error",
        )
    return redirect(url_for(".item_acl_report"))
