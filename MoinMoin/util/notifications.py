# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Notifications
"""

from io import BytesIO

from blinker import ANY
from urlparse import urljoin
from whoosh.query import Term, And

from flask import url_for, g as flaskg

from MoinMoin.constants.keys import (ACTION_COPY, ACTION_RENAME, ACTION_REVERT,
                                     ACTION_SAVE, ACTION_TRASH, ALL_REVS, CONTENTTYPE,
                                     MTIME, NAME_EXACT, WIKINAME)
from MoinMoin.i18n import _, L_, N_
from MoinMoin.i18n import force_locale
from MoinMoin.items.content import Content
from MoinMoin.mail.sendmail import sendmail
from MoinMoin.themes import render_template
from MoinMoin.signalling.signals import item_modified
from MoinMoin.util.subscriptions import get_subscribers
from MoinMoin.util.diff_datastruct import make_text_diff, diff as dict_diff
from MoinMoin.util.interwiki import url_for_item

from MoinMoin import log
logging = log.getLogger(__name__)

# additional action values
ACTION_CREATE = u"CREATE"
ACTION_MODIFY = u"MODIFY"

# destroy types
DESTROY_REV = u"DESTROY_REV"
DESTROY_ALL = u"DESTROY_ALL"


def msgs():
    """ Encapsulates the main notification messages

    :return: a dictionary of notification messages
    """
    _ = lambda x: x
    messages = {
        ACTION_CREATE: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been created by %(user_name)s:"),
        ACTION_MODIFY: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been modified by %(user_name)s:"),
        ACTION_RENAME: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been renamed by %(user_name)s:"),
        ACTION_COPY: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been copied by %(user_name)s:"),
        ACTION_REVERT: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been reverted by %(user_name)s:"),
        ACTION_TRASH: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been deleted by %(user_name)s:"),
        DESTROY_REV: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has one revision destroyed by %(user_name)s:"),
        DESTROY_ALL: _("The '%(fqname)s' ('%(item_url)s') item on '%(wiki_name)s' has been destroyed by %(user_name)s:"),
    }
    return messages

MESSAGES = msgs()


class Notification(object):
    """
    Represents a mail notification about an item change
    """
    txt_template = "mail/notification.txt"
    html_template = "mail/notification_main.html"

    def __init__(self, app, fqname, revs, **kwargs):
        self.app = app
        self.fqname = fqname
        self.revs = revs
        self.action = kwargs.get('action', None)
        self.content = kwargs.get('content', None)
        self.meta = kwargs.get('meta', None)
        self.comment = kwargs.get('comment', None)
        self.wiki_name = self.app.cfg.interwikiname

        if self.action == ACTION_SAVE:
            self.action = ACTION_CREATE if len(self.revs) == 1 else ACTION_MODIFY

        if self.action == ACTION_TRASH:
            self.meta = self.revs[0].meta

        kw = dict(fqname=unicode(fqname), wiki_name=self.wiki_name, user_name=flaskg.user.name0, item_url=url_for_item(self.fqname))
        self.notification_sentence = L_(MESSAGES[self.action], **kw)

    def get_content_diff(self):
        """ Create a content diff for the last item change

        :return: list of diff lines
        """
        if self.action in [DESTROY_REV, DESTROY_ALL, ]:
            contenttype = self.meta[CONTENTTYPE]
            oldfile, newfile = self.content, BytesIO("")
        elif self.action == ACTION_TRASH:
            contenttype = self.meta[CONTENTTYPE]
            oldfile, newfile = self.revs[0].data, BytesIO("")
        else:
            newfile = self.revs[0].data
            if len(self.revs) == 1:
                contenttype = self.revs[0].meta[CONTENTTYPE]
                oldfile = BytesIO("")
            else:
                from MoinMoin.apps.frontend.views import _common_type
                contenttype = _common_type(self.revs[0].meta[CONTENTTYPE], self.revs[1].meta[CONTENTTYPE])
                oldfile = self.revs[1].data
        content = Content.create(contenttype)
        return content._get_data_diff_text(oldfile, newfile)

    def get_meta_diff(self):
        """ Create a meta diff for the last item change

        :return: a list of tuples of the format (<change type>, <basekeys>, <value>)
                 that can be used to format a diff
        """
        if self.action in [ACTION_TRASH, DESTROY_REV, DESTROY_ALL, ]:
            old_meta, new_meta = dict(self.meta), dict()
        else:
            new_meta = dict(self.revs[0].meta)
            if len(self.revs) == 1:
                old_meta = dict()
            else:
                old_meta = dict(self.revs[1].meta)
        meta_diff = dict_diff(old_meta, new_meta)
        return meta_diff

    def generate_diff_url(self, domain):
        """ Generate the URL that leads to diff page of the last 2 revisions

        :param domain: domain name
        :return: the absolute URL to the diff page
        """
        if len(self.revs) < 2:
            return u""
        else:
            revid1 = self.revs[1].revid
            revid2 = self.revs[0].revid
        diff_rel_url = url_for('frontend.diff', item_name=self.fqname, rev1=revid1, rev2=revid2)
        return urljoin(domain, diff_rel_url)

    def render_templates(self, content_diff, meta_diff):
        """ Render both plain text and HTML templates by providing all the
        necessary arguments

        :return: tuple consisting of plain text and HTML notification message
         """
        meta_diff_txt = list(make_text_diff(meta_diff))
        domain = self.app.cfg.interwiki_map[self.app.cfg.interwikiname]
        unsubscribe_url = urljoin(domain, url_for('frontend.subscribe_item',
                                                  item_name=self.fqname))
        diff_url = self.generate_diff_url(domain)
        item_url = urljoin(domain, url_for('frontend.show_item', item_name=self.fqname))
        if self.comment is not None:
            comment = self.meta["comment"]
        else:
            comment = self.revs[0].meta["comment"]
        txt_template = render_template(Notification.txt_template,
                                       wiki_name=self.wiki_name,
                                       notification_sentence=self.notification_sentence,
                                       diff_url=diff_url,
                                       item_url=item_url,
                                       comment=comment,
                                       content_diff_=content_diff,
                                       meta_diff_=meta_diff_txt,
                                       unsubscribe_url=unsubscribe_url,
                                       )
        html_template = render_template(Notification.html_template,
                                        wiki_name=self.wiki_name,
                                        notification_sentence=self.notification_sentence,
                                        diff_url=diff_url,
                                        item_url=item_url,
                                        comment=comment,
                                        content_diff_=content_diff,
                                        meta_diff_=meta_diff,
                                        unsubscribe_url=unsubscribe_url,
        )
        return txt_template, html_template


def get_item_last_revisions(app, fqname):
    """ Get 2 or less most recent item revisions from the index

    :param app: local proxy app
    :param fqname: the fqname of the item
    :return: a list of revisions
    """
    terms = [Term(WIKINAME, app.cfg.interwikiname), Term(fqname.field, fqname.value), ]
    query = And(terms)
    return list(
        flaskg.storage.search(query, idx_name=ALL_REVS, sortedby=[MTIME],
                              reverse=True, limit=2))


@item_modified.connect_via(ANY)
def send_notifications(app, fqname, **kwargs):
    """ Send mail notifications to subscribers on item change

    :param app: local proxy app
    :param fqname: fqname of the changed item
    :param kwargs: key/value pairs that contain extra information about the item
                   required in order to create a notification
    """
    action = kwargs.get('action')
    revs = get_item_last_revisions(app, fqname) if action not in [
        DESTROY_REV, DESTROY_ALL, ] else []
    notification = Notification(app, fqname, revs, **kwargs)
    content_diff = notification.get_content_diff()
    meta_diff = notification.get_meta_diff()

    u = flaskg.user
    meta = kwargs.get('meta') if action in [DESTROY_REV, DESTROY_ALL, ] else revs[0].meta._meta
    subscribers = {subscriber for subscriber in get_subscribers(**meta) if
                   subscriber.itemid != u.itemid}
    subscribers_locale = {subscriber.locale for subscriber in subscribers}
    for locale in subscribers_locale:
        with force_locale(locale):
            txt_msg, html_msg = notification.render_templates(content_diff, meta_diff)
            subject = L_('[%(moin_name)s] Update of "%(fqname)s" by %(user_name)s',
                         moin_name=app.cfg.interwikiname, fqname=unicode(fqname), user_name=u.name0)
            subscribers_emails = [subscriber.email for subscriber in subscribers
                                  if subscriber.locale == locale]
            sendmail(subject, txt_msg, to=subscribers_emails, html=html_msg)
