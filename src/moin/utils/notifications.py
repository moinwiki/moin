# Copyright: 2013 MoinMoin:AnaBalica
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Notifications
"""

from io import BytesIO

from blinker import ANY
from urllib.parse import urljoin

from flask import url_for, g as flaskg
from flask import abort

from moin.constants.keys import (
    ACTION_COPY,
    ACTION_RENAME,
    ACTION_REVERT,
    ACTION_CONVERT,
    ACTION_SAVE,
    ACTION_TRASH,
    CONTENTTYPE,
)
from moin.i18n import _, L_
from moin.i18n import force_locale
from moin.items.content import Content
from moin.mail.sendmail import sendmail
from moin.themes import render_template
from moin.signalling.signals import item_modified
from moin.utils.subscriptions import get_subscribers
from moin.utils.diff_datastruct import make_text_diff, diff as dict_diff
from moin.utils.interwiki import url_for_item

from moin import log

logging = log.getLogger(__name__)

# additional action values
ACTION_CREATE = "CREATE"
ACTION_MODIFY = "MODIFY"

# destroy types
DESTROY_REV = "DESTROY_REV"
DESTROY_ALL = "DESTROY_ALL"


def msgs():
    """Encapsulates the main notification messages

    :return: a dictionary of notification messages
    """
    _ = lambda x: x  # noqa
    messages = {
        ACTION_CREATE: _("The '{fqname}' item on '{wiki_name}' has been created by {user_name}:"),
        ACTION_MODIFY: _("The '{fqname}' item on '{wiki_name}' has been modified by {user_name}:"),
        ACTION_RENAME: _("The '{fqname}' item on '{wiki_name}' has been renamed by {user_name}:"),
        ACTION_COPY: _("The '{fqname}' item on '{wiki_name}' has been copied by {user_name}:"),
        ACTION_CONVERT: _("The '{fqname}' item on '{wiki_name}' has been converted by {user_name}:"),
        ACTION_REVERT: _("The '{fqname}' item on '{wiki_name}' has been reverted by {user_name}:"),
        ACTION_TRASH: _("The '{fqname}' item on '{wiki_name}' has been deleted by {user_name}:"),
        DESTROY_REV: _("The '{fqname}' item on '{wiki_name}' has one revision destroyed by {user_name}:"),
        DESTROY_ALL: _("The '{fqname}' item on '{wiki_name}' has been destroyed by {user_name}:"),
    }
    return messages


MESSAGES = msgs()


class Notification:
    """
    Represents a mail notification about an item change
    """

    txt_template = "mail/notification.txt"
    html_template = "mail/notification_main.html"

    def __init__(self, app, fqname, action, data, meta, new_data, new_meta, **kwargs):
        self.app = app
        self.fqname = fqname
        self.action = action
        self.data = data
        self.meta = meta
        self.new_meta = new_meta
        self.new_data = new_data
        self.comment = kwargs.get("comment", None)
        self.wiki_name = self.app.cfg.interwikiname

        if self.action == ACTION_SAVE:
            self.action = ACTION_CREATE if meta is None else ACTION_MODIFY

        kw = dict(
            fqname=str(fqname),
            wiki_name=self.wiki_name,
            user_name=flaskg.user.name0,
            item_url=url_for_item(self.fqname),
        )
        self.notification_sentence = L_(MESSAGES[self.action]).format(**kw)

    def get_content_diff(self):
        """Create a content diff for the last item change

        :return: list of diff lines
        """
        if self.action in [ACTION_TRASH, DESTROY_REV, DESTROY_ALL]:
            contenttype = self.meta[CONTENTTYPE]
            oldfile, newfile = self.data, BytesIO(b"")
        else:
            if self.new_data:
                newfile = self.new_data
                newfile.seek(0)
                if self.meta is None:
                    contenttype = self.new_meta[CONTENTTYPE]
                    oldfile = BytesIO(b"")
                else:
                    from moin.apps.frontend.views import _common_type

                    contenttype = _common_type(self.new_meta[CONTENTTYPE], self.meta[CONTENTTYPE])
                    oldfile = self.data
            else:
                abort(403)
        content = Content.create(contenttype)
        return content._get_data_diff_text(oldfile, newfile)

    def get_meta_diff(self):
        """Create a meta diff for the last item change

        :return: a list of tuples of the format (<change type>, <basekeys>, <value>)
                 that can be used to format a diff
        """
        if self.action in [ACTION_TRASH, DESTROY_REV, DESTROY_ALL]:
            old_meta, new_meta = dict(self.meta), dict()
        else:
            new_meta = dict(self.new_meta)
            if self.meta is None:
                old_meta = dict()
            else:
                old_meta = dict(self.meta)
        meta_diff = dict_diff(old_meta, new_meta)
        return meta_diff

    def generate_diff_url(self, domain):
        """Generate the URL that leads to diff page of the last 2 revisions

        :param domain: domain name
        :return: the absolute URL to the diff page

        if data/meta are None, then new item is being created
        if new_data/new_meta is None then item is being deleted or destroyed
        """
        if self.new_data is None or self.data is None:
            return ""
        diff_rel_url = url_for(
            "frontend.diff", item_name=self.fqname, rev1=self.meta["revid"], rev2=self.new_meta["revid"]
        )
        return urljoin(domain, diff_rel_url)

    def render_templates(self, content_diff, meta_diff):
        """Render both plain text and HTML templates by providing all the
        necessary arguments

        :return: tuple consisting of plain text and HTML notification message
        """
        meta_diff_txt = list(make_text_diff(meta_diff))
        domain = self.app.cfg.interwiki_map[self.app.cfg.interwikiname]
        unsubscribe_url = urljoin(domain, url_for("frontend.subscribe_item", item_name=self.fqname))
        diff_url = self.generate_diff_url(domain)
        item_url = urljoin(domain, url_for("frontend.show_item", item_name=self.fqname))
        txt_template = render_template(
            Notification.txt_template,
            wiki_name=self.wiki_name,
            notification_sentence=self.notification_sentence,
            diff_url=diff_url,
            item_url=item_url,
            comment=self.comment,
            content_diff_=content_diff,
            meta_diff_=meta_diff_txt,
            unsubscribe_url=unsubscribe_url,
        )
        html_template = render_template(
            Notification.html_template,
            wiki_name=self.wiki_name,
            notification_sentence=self.notification_sentence,
            diff_url=diff_url,
            item_url=item_url,
            comment=self.comment,
            content_diff_=content_diff,
            meta_diff_=meta_diff,
            unsubscribe_url=unsubscribe_url,
        )
        return txt_template, html_template


@item_modified.connect_via(ANY)
def send_notifications(app, fqname, action, data=None, meta=None, new_data=None, new_meta=None, **kwargs):
    """Send mail notifications to subscribers on item change

    :param app: local proxy app
    :param fqname: fqname of the changed item
    :param action: type of modification - save, rename, destroy...
    :param data: the item's data, None if item is new
    :param meta: the item's meta data, None if item is new
    :param new_data: open file with new data, None if action is delete or destroy
    :param new_meta: new meta data, None if action is delete or destroy
    :param kwargs: optional comment
    """
    if new_meta is None:
        subscribers = {subscriber for subscriber in get_subscribers(**meta) if subscriber.itemid != flaskg.user.itemid}
    else:
        subscribers = {
            subscriber for subscriber in get_subscribers(**new_meta) if subscriber.itemid != flaskg.user.itemid
        }
    if not subscribers:
        return
    notification = Notification(app, fqname, action, data, meta, new_data, new_meta, **kwargs)
    try:
        content_diff = notification.get_content_diff()
    except Exception:
        # current user has likely corrupted an item or fixed a corrupted item
        # if current item is corrupt, another exception will occur in a downstream script
        content_diff = ["- " + _("An error has occurred, the current or prior revision of this item may be corrupt.")]
    meta_diff = notification.get_meta_diff()
    subscribers_locale = {subscriber.locale for subscriber in subscribers}
    for locale in subscribers_locale:
        with force_locale(locale):
            txt_msg, html_msg = notification.render_templates(content_diff, meta_diff)
            subject = _('[{moin_name}] Update of "{fqname}" by {user_name}').format(
                moin_name=app.cfg.interwikiname, fqname=str(fqname), user_name=flaskg.user.name0
            )
            subscribers_emails = [subscriber.email for subscriber in subscribers if subscriber.locale == locale]
            sendmail(subject, txt_msg, to=subscribers_emails, html=html_msg)
