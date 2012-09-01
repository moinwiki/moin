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

import time
import itertools
import json
from StringIO import StringIO
from collections import namedtuple

from flask import current_app as app
from flask import g as flaskg
from flask import request, Response, redirect, abort, escape

from flatland import Form

from jinja2 import Markup

from whoosh.query import Term, And, Prefix

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.security.textcha import TextCha, TextChaizedForm
from MoinMoin.signalling import item_modified
from MoinMoin.storage.middleware.protecting import AccessDenied
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, StorageError
from MoinMoin.i18n import L_
from MoinMoin.themes import render_template
from MoinMoin.util.interwiki import url_for_item
from MoinMoin.util.registry import RegistryBase
from MoinMoin.forms import RequiredText, OptionalText, JSON, Tags, Submit
from MoinMoin.constants.keys import (
    NAME, NAME_OLD, NAME_EXACT, WIKINAME, MTIME, SYSITEM_VERSION, ITEMTYPE,
    CONTENTTYPE, SIZE, ACTION, ADDRESS, HOSTNAME, USERID, COMMENT,
    HASH_ALGORITHM, ITEMID, REVID, DATAID, CURRENT, PARENTID
    )
from MoinMoin.constants.contenttypes import charset, CONTENTTYPE_GROUPS
from MoinMoin.constants.itemtypes import ITEMTYPES

from .content import Content, NonExistentContent, Draw


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
    def __init__(self, item, itemtype=None, contenttype=None):
        self.item = item
        self.meta = {
            ITEMTYPE: itemtype or u'nonexistent',
            CONTENTTYPE: contenttype or u'application/x-nonexistent'
        }
        self.data = StringIO('')
        self.revid = None
        if self.item:
            self.meta[NAME] = self.item.name


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


class BaseModifyForm(BaseChangeForm):
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


IndexEntry = namedtuple('IndexEntry', 'relname meta hassubitems')

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
        old_prefixlen = len(self.subitems_prefix)
        new_prefix = name + '/'
        for child in self.get_subitem_revs():
            child_oldname = child.meta[NAME]
            child_newname = new_prefix + child_oldname[old_prefixlen:]
            item = Item.create(child_oldname)
            item._save(item.meta, item.content.data, name=child_newname, action=action, comment=comment)

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

    class _ModifyForm(BaseModifyForm):
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

    @property
    def subitems_prefix(self):
        return self.name + u'/' if self.name else u''

    def get_subitem_revs(self):
        """
        Create a list of subitems of this item.

        Subitems are in the form of storage Revisions.
        """
        query = Term(WIKINAME, app.cfg.interwikiname)
        # trick: an item of empty name can be considered as "virtual root item"
        # that has all wiki items as sub items
        if self.name:
            query = And([query, Prefix(NAME_EXACT, self.subitems_prefix)])
        revs = flaskg.storage.search(query, sortedby=NAME_EXACT, limit=None)
        return revs

    def make_flat_index(self, subitems):
        """
        Create a list of IndexEntry from a list of subitems.

        The resulting list contains only IndexEntry for *direct* subitems, e.g.
        'foo' but not 'foo/bar'. When the latter is encountered, the former has
        its `hassubitems` flag set in its IndexEntry.

        When disconnected levels are detected, e.g. when there is foo/bar but no
        foo, a dummy IndexEntry is created for the latter, with 'nonexistent'
        itemtype and 'application/x.nonexistent' contenttype. Its `hassubitems`
        flag is also set.
        """
        prefix = self.subitems_prefix
        prefixlen = len(prefix)
        index = []

        # relnames of all encountered subitems
        relnames = set()
        # relnames of subitems that need to have `hassubitems` flag set (but didn't)
        relnames_to_patch = set()

        for rev in subitems:
            fullname = rev.meta[NAME]
            relname = fullname[prefixlen:]
            if '/' in relname:
                # Find the *direct* subitem that is the ancestor of current
                # (indirect) subitem. e.g. suppose when the index root is
                # 'foo', and current item (`rev`) is 'foo/bar/lorem/ipsum',
                # 'foo/bar' will be found.
                direct_relname = relname.partition('/')[0]
                direct_fullname = prefix + direct_relname
                if direct_relname not in relnames:
                    # Join disconnected level with a dummy IndexEntry.
                    # NOTE: Patching the index when encountering a disconnected
                    # subitem might break the ordering. e.g. suppose the global
                    # index has ['lorem-', 'lorem/ipsum'] (thus 'lorem' is a
                    # disconnected level; also, note that ord('-') < ord('/'))
                    # the patched index will have lorem after lorem-, requiring
                    # one more pass of sorting after generating the index.
                    e = IndexEntry(direct_relname, DummyRev(DummyItem(direct_fullname)).meta, True)
                    index.append(e)
                    relnames.add(direct_relname)
                else:
                    relnames_to_patch.add(direct_relname)
            else:
                e = IndexEntry(relname, rev.meta, False)
                index.append(e)
                relnames.add(relname)

        for i in xrange(len(index)):
            if index[i].relname in relnames_to_patch:
                index[i] = index[i]._replace(hassubitems=True)

        return index

    def filter_index(self, index, startswith=None, selected_groups=None):
        """
        Filter a list of IndexEntry.

        :param startswith: if set, only items whose names start with startswith
                           are selected.
        :param selected_groups: if set, only items whose contentypes belong to
                                the selected contenttype_groups are selected.
        """
        if startswith is not None:
            index = [e for e in index
                     if e.relname.startswith((startswith, startswith.swapcase()))]

        def build_contenttypes(groups):
            ctypes = [[ctype for ctype, clabel in contenttypes]
                      for gname, contenttypes in CONTENTTYPE_GROUPS
                      if gname in groups]
            ctypes_chain = itertools.chain(*ctypes)
            contenttypes = list(ctypes_chain)
            contenttypes_without_encoding = [contenttype[:contenttype.index(u';')]
                                             for contenttype in contenttypes
                                             if u';' in contenttype]
            contenttypes.extend(contenttypes_without_encoding) # adding more mime-types without the encoding term
            return contenttypes

        if selected_groups is not None:
            all_groups = [gname for gname, contenttypes in CONTENTTYPE_GROUPS]
            selected_contenttypes = build_contenttypes(selected_groups)
            filtered_index = [e for e in index
                              if e.meta[CONTENTTYPE] in selected_contenttypes]

            unknown_item_group = "unknown items"
            if unknown_item_group in selected_groups:
                all_contenttypes = build_contenttypes(all_groups)
                filtered_index.extend([e for e in index
                                       if e.meta[CONTENTTYPE] not in all_contenttypes])

            index = filtered_index
        return index

    def get_index(self, startswith=None, selected_groups=None):
        return self.filter_index(self.make_flat_index(self.get_subitem_revs()), startswith, selected_groups)

    index_template = 'index.html'

    def name_initial(self, subitems):
        prefixlen = len(self.subitems_prefix)
        initials = [(item.meta[NAME][prefixlen]) for item in subitems]
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
        class C(self._ModifyForm):
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

    def do_show(self, revid):
        show_revision = revid != CURRENT
        show_navigation = False # TODO
        first_rev = last_rev = None # TODO
        return render_template(self.show_template,
                               item=self, item_name=self.name,
                               rev=self.rev,
                               contenttype=self.contenttype,
                               first_rev_id=first_rev,
                               last_rev_id=last_rev,
                               data_rendered=Markup(self.content._render_data()),
                               show_revision=show_revision,
                               show_navigation=show_navigation,
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

    show_template = 'show.html'
    modify_template = 'modify.html'


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

    def do_show(self, revid):
        # First, check if the current user has the required privileges
        if flaskg.user.may.create(self.name):
            content = self._select_itemtype()
        else:
            content = render_template('show_nonexistent.html',
                                      item_name=self.name,
                                     )
        return Response(content, 404)

    def do_modify(self):
        # First, check if the current user has the required privileges
        if not flaskg.user.may.create(self.name):
            abort(403)
        return self._select_itemtype()

    def _select_itemtype(self):
        return render_template('modify_select_itemtype.html',
                               item_name=self.name,
                               itemtypes=ITEMTYPES,
                              )


from ..util.pysupport import load_package_modules
load_package_modules(__name__, __path__)
