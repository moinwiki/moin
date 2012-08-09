# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2009 MoinMoin:ThomasWaldmann
# Copyright: 2009-2011 MoinMoin:ReimarBauer
# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2008,2009 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - high-level (frontend) items

    While MoinMoin.storage cares for backend storage of items,
    this module cares for more high-level, frontend items,
    e.g. showing, editing, etc. of wiki items.

    Each class in this module corresponds to an itemtype.
"""

import re, time
import itertools
import json
from StringIO import StringIO
from collections import namedtuple
from functools import partial

from flatland import Form
from flatland.validation import Validator

from whoosh.query import Term, And, Prefix

from MoinMoin.forms import RequiredText, OptionalText, JSON, Tags, Submit

from MoinMoin.security.textcha import TextCha, TextChaizedForm
from MoinMoin.signalling import item_modified
from MoinMoin.util.mime import Type
from MoinMoin.storage.middleware.protecting import AccessDenied

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import g as flaskg

from flask import request, Response, redirect, abort, escape

from werkzeug import is_resource_modified

from MoinMoin.i18n import L_
from MoinMoin.themes import render_template
from MoinMoin.util.interwiki import url_for_item
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, StorageError
from MoinMoin.util.registry import RegistryBase
from MoinMoin.constants.keys import (
    NAME, NAME_OLD, NAME_EXACT, WIKINAME, MTIME, SYSITEM_VERSION, ITEMTYPE,
    CONTENTTYPE, SIZE, TAGS, ACTION, ADDRESS, HOSTNAME, USERID, COMMENT,
    HASH_ALGORITHM, ITEMID, REVID, DATAID, CURRENT, PARENTID
    )
from MoinMoin.constants.contenttypes import charset, CONTENTTYPE_GROUPS

from .content import Content, NonExistentContent, Draw, content_registry


COLS = 80
ROWS_META = 10


class RegistryItem(RegistryBase):
    class Entry(namedtuple('Entry', 'factory itemtype priority')):
        def __call__(self, itemtype, *args, **kw):
            if self.itemtype == itemtype:
                return self.factory(*args, **kw)

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                if self.priority != other.priority:
                    return self.priority < other.priority
                return self.itemtype < other.itemtype
            return NotImplemented

    def register(self, factory, itemtype, priority=RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        :param factory: Factory to register. Callable, must return an object.
        """
        return self._register(self.Entry(factory, itemtype, priority))


item_registry = RegistryItem()

def register(cls):
    item_registry.register(cls._factory, cls.itemtype)
    return cls


class DummyRev(dict):
    """ if we have no stored Revision, we use this dummy """
    def __init__(self, item, itemtype, contenttype):
        self.item = item
        self.meta = {ITEMTYPE: itemtype, CONTENTTYPE: contenttype}
        self.data = StringIO('')
        self.revid = None


class DummyItem(object):
    """ if we have no stored Item, we use this dummy """
    def __init__(self, name):
        self.name = name
    def list_revisions(self):
        return [] # same as an empty Item
    def destroy_all_revisions(self):
        return True


class BaseChangeForm(TextChaizedForm):
    comment = OptionalText.using(label=L_('Comment')).with_properties(placeholder=L_("Comment about your change"))
    submit = Submit


class BaseMetaForm(Form):
    itemtype = RequiredText.using(label=L_("Item type")).with_properties(placeholder=L_("Item type"))
    contenttype = RequiredText.using(label=L_("Content type")).with_properties(placeholder=L_("Content type"))
    # Disabled - Flatland doesn't distinguish emtpy value and nonexistent
    # value, while an emtpy acl and no acl have different semantics
    #acl = OptionalText.using(label=L_('ACL')).with_properties(placeholder=L_("Access Control List"))
    summary = OptionalText.using(label=L_("Summary")).with_properties(placeholder=L_("One-line summary of the item"))
    tags = Tags


class Item(object):
    """ Highlevel (not storage) Item, wraps around a storage Revision"""
    @classmethod
    def _factory(cls, *args, **kw):
        return cls(*args, **kw)

    @classmethod
    def create(cls, name=u'', itemtype=None, contenttype=None, rev_id=CURRENT, item=None):
        """
        Create a highlevel Item by looking up :name or directly wrapping
        :item and extract the Revision designated by :rev_id revision.

        The highlevel Item is created by creating an instance of Content
        subclass according to the item's contenttype metadata entry; The
        :contenttype argument can be used to override contenttype. It is used
        only when handling +convert (when deciding the contenttype of target
        item), +modify (when creating a new item whose contenttype is not yet
        decided), +diff and +diffraw (to coerce the Content to a common
        super-contenttype of both revisions).

        After that the Content instance, an instance of Item subclass is
        created according to the item's itemtype metadata entry, and the
        previously created Content instance is assigned to its content
        property.
        """
        if contenttype is None:
            contenttype = u'application/x-nonexistent'
        if itemtype is None:
            itemtype = u'nonexistent'
        if 1: # try:
            if item is None:
                item = flaskg.storage[name]
            else:
                name = item.name
        if not item: # except NoSuchItemError:
            logging.debug("No such item: {0!r}".format(name))
            item = DummyItem(name)
            rev = DummyRev(item, itemtype, contenttype)
            logging.debug("Item {0!r}, created dummy revision with contenttype {1!r}".format(name, contenttype))
        else:
            logging.debug("Got item: {0!r}".format(name))
            try:
                rev = item.get_revision(rev_id)
                contenttype = u'application/octet-stream' # it exists
                itemtype = u'default' # default itemtype to u'default' for compatibility
            except KeyError: # NoSuchRevisionError:
                try:
                    rev = item.get_revision(CURRENT) # fall back to current revision
                    # XXX add some message about invalid revision
                except KeyError: # NoSuchRevisionError:
                    logging.debug("Item {0!r} has no revisions.".format(name))
                    rev = DummyRev(item, itemtype, contenttype)
                    logging.debug("Item {0!r}, created dummy revision with contenttype {1!r}".format(name, contenttype))
            logging.debug("Got item {0!r}, revision: {1!r}".format(name, rev_id))
        contenttype = rev.meta.get(CONTENTTYPE) or contenttype # use contenttype in case our metadata does not provide CONTENTTYPE
        logging.debug("Item {0!r}, got contenttype {1!r} from revision meta".format(name, contenttype))
        #logging.debug("Item %r, rev meta dict: %r" % (name, dict(rev.meta)))

        # XXX Cannot pass item=item to Content.__init__ via
        # content_registry.get yet, have to patch it later.
        content = Content.create(contenttype)

        itemtype = rev.meta.get(ITEMTYPE) or itemtype
        logging.debug("Item {0!r}, got itemtype {1!r} from revision meta".format(name, itemtype))

        item = item_registry.get(itemtype, name, rev=rev, content=content)
        logging.debug("Item class {0!r} handles {1!r}".format(item.__class__, itemtype))

        content.item = item

        return item

    def __init__(self, name, rev=None, content=None):
        self.name = name
        self.rev = rev
        self.content = content

    def get_meta(self):
        return self.rev.meta
    meta = property(fget=get_meta)

    # XXX Backward compatibility, remove soon
    @property
    def contenttype(self):
        return self.content.contenttype if self.content else None

    def _render_meta(self):
        return "<pre>{0}</pre>".format(escape(self.meta_dict_to_text(self.meta, use_filter=False)))

    def meta_filter(self, meta):
        """ kill metadata entries that we set automatically when saving """
        kill_keys = [# shall not get copied from old rev to new rev
            SYSITEM_VERSION,
            NAME_OLD,
            # are automatically implanted when saving
            NAME,
            ITEMID, REVID, DATAID,
            HASH_ALGORITHM,
            SIZE,
            COMMENT,
            MTIME,
            ACTION,
            ADDRESS, HOSTNAME, USERID,
            ]
        for key in kill_keys:
            meta.pop(key, None)
        return meta

    def meta_text_to_dict(self, text):
        """ convert meta data from a text fragment to a dict """
        meta = json.loads(text)
        return self.meta_filter(meta)

    def meta_dict_to_text(self, meta, use_filter=True):
        """ convert meta data from a dict to a text fragment """
        meta = dict(meta)
        if use_filter:
            meta = self.meta_filter(meta)
        return json.dumps(meta, sort_keys=True, indent=2, ensure_ascii=False)

    def prepare_meta_for_modify(self, meta):
        """
        transform the meta dict of the current revision into a meta dict
        that can be used for savind next revision (after "modify").
        """
        meta = dict(meta)
        revid = meta.pop(REVID, None)
        if revid is not None:
            meta[PARENTID] = revid
        return meta

    def _rename(self, name, comment, action):
        self._save(self.meta, self.content.data, name=name, action=action, comment=comment)
        for child in self.get_index():
            item = Item.create(child[0])
            item._save(item.meta, item.content.data, name='/'.join((name, child[1])), action=action, comment=comment)

    def rename(self, name, comment=u''):
        """
        rename this item to item <name>
        """
        return self._rename(name, comment, action=u'RENAME')

    def delete(self, comment=u''):
        """
        delete this item
        """
        trash_prefix = u'Trash/' # XXX move to config
        now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        # make trash name unique by including timestamp:
        trashname = u'{0}{1} ({2} UTC)'.format(trash_prefix, self.name, now)
        return self._rename(trashname, comment, action=u'TRASH')

    def revert(self, comment=u''):
        return self._save(self.meta, self.content.data, action=u'REVERT', comment=comment)

    def destroy(self, comment=u'', destroy_item=False):
        # called from destroy UI/POST
        if destroy_item:
            # destroy complete item with all revisions, metadata, etc.
            self.rev.item.destroy_all_revisions()
        else:
            # just destroy this revision
            self.rev.item.destroy_revision(self.rev.revid)

    def modify(self, meta, data, comment=u'', contenttype_guessed=None, contenttype_qs=None):
        if contenttype_qs:
            # we use querystring param to FORCE content type
            meta[CONTENTTYPE] = contenttype_qs

        return self._save(meta, data, contenttype_guessed=contenttype_guessed, comment=comment)

    class _ModifyForm(BaseChangeForm):
        """Base class for ModifyForm of Item subclasses."""
        meta_form = BaseMetaForm
        extra_meta_text = JSON.using(label=L_("Extra MetaData (JSON)")).with_properties(rows=ROWS_META, cols=COLS)
        meta_template = 'modify_meta.html'

        def _load(self, item):
            meta = item.prepare_meta_for_modify(item.meta)
            # Default value of `policy` argument of Flatland.Dict.set's is
            # 'strict', which causes KeyError to be thrown when meta contains
            # meta keys that are not present in self['meta_form']. Setting
            # policy to 'duck' suppresses this behavior.
            self['meta_form'].set(meta, policy='duck')
            for k in self['meta_form'].field_schema_mapping.keys():
                meta.pop(k, None)
            self['extra_meta_text'].set(item.meta_dict_to_text(meta))
            self['content_form']._load(item.content)

        def _dump(self, item):
            meta = self['meta_form'].value.copy()
            meta.update(item.meta_text_to_dict(self['extra_meta_text'].value))
            data, contenttype_guessed = self['content_form']._dump(item.content)
            comment = self['comment'].value
            return meta, data, contenttype_guessed, comment

        @classmethod
        def from_item(cls, item):
            form = cls.from_defaults()
            TextCha(form).amend_form()
            form._load(item)
            return form

        @classmethod
        def from_request(cls, request):
            form = cls.from_flat(request.form.items() + request.files.items())
            TextCha(form).amend_form()
            return form

    def do_modify(self):
        """
        Handle +modify requests, both GET and POST.

        This method should be overridden in subclasses, providing polymorphic
        behavior for the +modify view.
        """
        raise NotImplementedError

    def _save(self, meta, data=None, name=None, action=u'SAVE', contenttype_guessed=None, comment=u'', overwrite=False):
        backend = flaskg.storage
        storage_item = backend[self.name]
        try:
            currentrev = storage_item.get_revision(CURRENT)
            rev_id = currentrev.revid
            contenttype_current = currentrev.meta.get(CONTENTTYPE)
        except KeyError: # XXX was: NoSuchRevisionError:
            currentrev = None
            rev_id = None
            contenttype_current = None

        meta = dict(meta) # we may get a read-only dict-like, copy it

        # we store the previous (if different) and current item name into revision metadata
        # this is useful for rename history and backends that use item uids internally
        if name is None:
            name = self.name
        oldname = meta.get(NAME)
        if oldname and oldname != name:
            meta[NAME_OLD] = oldname
        meta[NAME] = name

        if comment:
            meta[COMMENT] = unicode(comment)

        if not overwrite and REVID in meta:
            # we usually want to create a new revision, thus we must remove the existing REVID
            del meta[REVID]

        if data is None:
            if currentrev is not None:
                # we don't have (new) data, just copy the old one.
                # a valid usecase of this is to just edit metadata.
                data = currentrev.data
            else:
                data = ''

        if isinstance(data, unicode):
            data = data.encode(charset) # XXX wrong! if contenttype gives a coding, we MUST use THAT.

        if isinstance(data, str):
            data = StringIO(data)

        newrev = storage_item.store_revision(meta, data, overwrite=overwrite,
                                             action=unicode(action),
                                             contenttype_current=contenttype_current,
                                             contenttype_guessed=contenttype_guessed,
                                             )
        item_modified.send(app._get_current_object(), item_name=name)
        return newrev.revid, newrev.meta[SIZE]

    def get_index(self):
        """ create an index of sub items of this item """
        if self.name:
            prefix = self.name + u'/'
            query = And([Term(WIKINAME, app.cfg.interwikiname), Prefix(NAME_EXACT, prefix)])
        else:
            # trick: an item of empty name can be considered as "virtual root item",
            # that has all wiki items as sub items
            prefix = u''
            query = Term(WIKINAME, app.cfg.interwikiname)
        # We only want the sub-item part of the item names, not the whole item objects.
        prefix_len = len(prefix)
        revs = flaskg.storage.search(query, sortedby=NAME_EXACT, limit=None)
        items = [(rev.meta[NAME], rev.meta[NAME][prefix_len:], rev.meta[CONTENTTYPE])
                 for rev in revs]
        return items

    def _connect_levels(self, index):
        new_index = []
        last = self.name
        for item in index:
            name = item[0]

            while not name.startswith(last):
                last = last.rpartition('/')[0]

            missing_layers = name.split('/')[last.count('/')+1:-1]

            for layer in missing_layers:
                last = '/'.join([last, layer])
                new_index.append((last, last[len(self.name)+1:], u'application/x-nonexistent'))

            last = item[0]
            new_index.append(item)

        return new_index

    def flat_index(self, startswith=None, selected_groups=None):
        """
        creates a top level index of sub items of this item
        if startswith is set, filtering is done on the basis of starting letter of item name
        if selected_groups is set, items whose contentype belonging to the selected contenttype_groups, are filtered.
        """
        index = self.get_index()
        index = self._connect_levels(index)

        all_ctypes = [[ctype for ctype, clabel in contenttypes]
                      for gname, contenttypes in CONTENTTYPE_GROUPS]
        all_ctypes_chain = itertools.chain(*all_ctypes)
        all_contenttypes = list(all_ctypes_chain)
        contenttypes_without_encoding = [contenttype[:contenttype.index(u';')]
                                         for contenttype in all_contenttypes
                                         if u';' in contenttype]
        all_contenttypes.extend(contenttypes_without_encoding) # adding more mime-types without the encoding term

        if selected_groups:
            ctypes = [[ctype for ctype, clabel in contenttypes]
                      for gname, contenttypes in CONTENTTYPE_GROUPS
                      if gname in selected_groups]
            ctypes_chain = itertools.chain(*ctypes)
            selected_contenttypes = list(ctypes_chain)
            contenttypes_without_encoding = [contenttype[:contenttype.index(u';')]
                                             for contenttype in selected_contenttypes
                                             if u';' in contenttype]
            selected_contenttypes.extend(contenttypes_without_encoding)
        else:
            selected_contenttypes = all_contenttypes

        unknown_item_group = "unknown items"
        if startswith:
            startswith = (u'{0}'.format(startswith), u'{0}'.format(startswith.swapcase()))
            if not selected_groups or unknown_item_group in selected_groups:
                index = [(fullname, relname, contenttype)
                         for fullname, relname, contenttype in index
                         if u'/' not in relname
                         and relname.startswith(startswith)
                         and (contenttype not in all_contenttypes or contenttype in selected_contenttypes)]
                         # If an item's contenttype not present in the default contenttype list,
                         # then it will be shown without going through any filter.
            else:
                index = [(fullname, relname, contenttype)
                         for fullname, relname, contenttype in index
                         if u'/' not in relname
                         and relname.startswith(startswith)
                         and (contenttype in selected_contenttypes)]

        else:
            if not selected_groups or unknown_item_group in selected_groups:
                index = [(fullname, relname, contenttype)
                         for fullname, relname, contenttype in index
                         if u'/' not in relname
                         and (contenttype not in all_contenttypes or contenttype in selected_contenttypes)]
            else:
                index = [(fullname, relname, contenttype)
                         for fullname, relname, contenttype in index
                         if u'/' not in relname
                         and contenttype in selected_contenttypes]

        return index

    index_template = 'index.html'

    def get_detailed_index(self, index):
        """ appends a flag in the index of items indicating that the parent has sub items """
        detailed_index = []
        all_item_index = self.get_index()
        all_item_text = "\n".join(item_info[1] for item_info in all_item_index)
        for fullname, relname, contenttype in index:
            hassubitem = False
            subitem_name_re = u"^{0}/[^/]+$".format(re.escape(relname))
            regex = re.compile(subitem_name_re, re.UNICODE|re.M)
            if regex.search(all_item_text):
                hassubitem = True
            detailed_index.append((fullname, relname, contenttype, hassubitem))
        return detailed_index

    def name_initial(self, names=None):
        initials = [(name[1][0])
                   for name in names]
        return initials

    delete_template = 'delete.html'
    destroy_template = 'destroy.html'
    diff_template = 'diff.html'
    rename_template = 'rename.html'
    revert_template = 'revert.html'


class Contentful(Item):
    """
    Base class for Item subclasses that have content.
    """
    @property
    def ModifyForm(self):
        class C(Item._ModifyForm):
            content_form = self.content.ModifyForm
        C.__name__ = 'ModifyForm'
        return C


@register
class Default(Contentful):
    """
    A "conventional" wiki item.
    """
    itemtype = u'default'

    def _do_modify_show_templates(self):
        # call this if the item is still empty
        rev_ids = []
        item_templates = self.content.get_templates(self.contenttype)
        return render_template('modify_select_template.html',
                               item_name=self.name,
                               itemtype=self.itemtype,
                               rev=self.rev,
                               contenttype=self.contenttype,
                               templates=item_templates,
                               first_rev_id=rev_ids and rev_ids[0],
                               last_rev_id=rev_ids and rev_ids[-1],
                               meta_rendered='',
                               data_rendered='',
                               )

    def do_modify(self):
        method = request.method
        if method == 'GET':
            if isinstance(self.content, NonExistentContent):
                return render_template('modify_select_contenttype.html',
                                       item_name=self.name,
                                       itemtype=self.itemtype,
                                       contenttype_groups=CONTENTTYPE_GROUPS,
                                      )
            item = self
            if isinstance(self.rev, DummyRev):
                template_name = request.values.get('template')
                if template_name is None:
                    return self._do_modify_show_templates()
                elif template_name:
                    item = Item.create(template_name)
            form = self.ModifyForm.from_item(item)
        elif method == 'POST':
            # XXX workaround for *Draw items
            if isinstance(self.content, Draw):
                try:
                    self.content.handle_post()
                except AccessDenied:
                    abort(403)
                else:
                    # *Draw Applets POSTs more than once, redirecting would
                    # break them
                    return "OK"
            form = self.ModifyForm.from_request(request)
            if form.validate():
                meta, data, contenttype_guessed, comment = form._dump(self)
                contenttype_qs = request.values.get('contenttype')
                try:
                    self.modify(meta, data, comment, contenttype_guessed, contenttype_qs)
                except AccessDenied:
                    abort(403)
                else:
                    return redirect(url_for_item(self.name))
        return render_template(self.modify_template,
                               item_name=self.name,
                               rows_meta=str(ROWS_META), cols=str(COLS),
                               form=form,
                               search_form=None,
                              )

    modify_template = 'modify.html'


@register
class Ticket(Contentful):
    """
    Stub for ticket item class.
    """
    itemtype = u'ticket'


@register
class Userprofile(Item):
    """
    Currently userprofile is implemented as a contenttype. This is a stub of an
    itemtype implementation of userprofile.
    """
    itemtype = u'userprofile'


@register
class NonExistent(Item):
    """
    A dummy Item for nonexistent items (when modifying, a nonexistent item with
    undetermined itemtype)
    """
    itemtype = u'nonexistent'

    def _convert(self, doc):
        abort(404)

    def do_modify(self):
        # First, check if the current user has the required privileges
        if not flaskg.user.may.create(self.name):
            abort(403)

        # TODO Construct this list from the item_registry. Two more fields (ie.
        # display name and description) are needed in the registry then to
        # support the automatic construction.
        ITEMTYPES = [
            (u'default', u'Default', 'Wiki item'),
            (u'ticket', u'Ticket', 'Ticket item'),
        ]

        return render_template('modify_select_itemtype.html',
                               item_name=self.name,
                               itemtypes=ITEMTYPES,
                              )
