"""
    MoinMoin - MemoryBackend + TracingBackend

    This module contains a simple Backend that stores all data in memory
    and a TracingBackend that can generate a python function that contains
    all recorded operations.

    This is mainly done for testing and documentation / demonstration purposes.
    Thus, this backend IS NOT designed for concurrent use.

    DO NOT (even for the smallest glimpse of a second) consider to use this
    backend for any production site that needs persistant storage.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:AlexanderSchremmer
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import StringIO
from threading import Lock
import time

from MoinMoin.storage import Backend as BackendBase
from MoinMoin.storage import Item as ItemBase
from MoinMoin.storage import StoredRevision as StoredRevisionBase
from MoinMoin.storage import NewRevision as NewRevisionBase
from MoinMoin.storage import Revision as RevisionBase

from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError


class Item(ItemBase):
    pass

class StoredRevision(StoredRevisionBase):
    pass

class NewRevision(NewRevisionBase):
    pass

class MemoryBackend(BackendBase):
    Item = Item
    StoredRevision = StoredRevision
    NewRevision = NewRevision
    """
    Implementation of the MemoryBackend. All data is kept in attributes of this
    class. As soon as the MemoryBackend-object goes out of scope, your data is LOST.

    Docstrings for the methods can be looked up in the superclass Backend, found
    in MoinMoin.storage.
    """
    def __init__(self, backend_uri=''):
        """
        Initialize this Backend.

        We accept a (unused) uri parameter, because other backends have this, too.
        """
        self._last_itemid = 0
        self._itemmap = {}                  # {itemname : itemid}   // names may change...
        self._item_metadata = {}            # {id : {metadata}}
        self._item_revisions = {}           # {id : {revision_id : (revision_data, {revision_metadata})}}
        self._item_metadata_lock = {}       # {id : Lockobject}
        self._revision_history = []

    def history(self, reverse=True):
        """
        @see: Backend.history.__doc__
        """
        if reverse:
            return iter(self._revision_history[::-1])
        else:
            return iter(self._revision_history)

    def get_item(self, itemname):
        """
        @see: Backend.get_item.__doc__
        """
        if not self.has_item(itemname):
            raise NoSuchItemError("No such item, %r" % (itemname))

        item = self.Item(self, itemname)
        item._item_id = self._itemmap[itemname]

        if not item._item_id in self._item_metadata:  # Maybe somebody already got an instance of this Item and thus there already is a Lock for that Item.
            self._item_metadata_lock[item._item_id] = Lock()

        return item

    def has_item(self, itemname):
        """
        @see: Backend.get_item.__doc__

        Overriding the default has_item-method because we can simply look the name
        up in our nice dictionary.
        Whenever possible, you should aim to override the dummy has_item-method.
        """
        return itemname in self._itemmap

    def create_item(self, itemname):
        """
        @see: Backend.create_item.__doc__

        Note: DON'T rely on the dummy has_item-method here.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))
        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An Item with the name %r already exists!" % (itemname))

        item = self.Item(self, itemname)
        item._item_id = None
        return item

    def _destroy_item(self, item):
        """
        @see: Backend._destroy_item.__doc__
        """
        item_map = self._itemmap
        item_meta = self._item_metadata
        item_revs = self._item_revisions
        item_lock = self._item_metadata_lock

        try:
            item_id = item_map[item.name]
            del item_map[item.name]
        except KeyError:
            # No need to proceed further. The item has already been destroyed by someone else.
            return

        for struct in (item_meta, item_revs, item_lock):
            try:
                del struct[item_id]
            except KeyError:
                pass

        # Create a new revision_history list first and then swap that atomically with
        # the old one (that still contains the item's revs).
        rev_hist = [rev for rev in self._revision_history if rev.item.name != item.name]
        self._revision_history = rev_hist

    def iteritems(self):
        """
        @see: Backend.iteritems.__doc__
        """
        for itemname in self._itemmap.keys():
            yield self.get_item(itemname)

    def _get_revision(self, item, revno):
        """
        @see: Backend._get_revision.__doc__
        """
        item_id = item._item_id
        revisions = item.list_revisions()

        if revno == -1 and revisions:
            revno = max(item.list_revisions())
        try:
            data = self._item_revisions[item_id][revno][0]
            metadata = self._item_revisions[item_id][revno][1]
        except KeyError:
            raise NoSuchRevisionError("No Revision #%d on Item %s - Available revisions: %r" % (revno, item.name, revisions))
        else:
            revision = self.StoredRevision(item, revno, timestamp=metadata['__timestamp'], size=len(data))
            revision._data = StringIO.StringIO(data)
            revision._metadata = metadata
            return revision

    def _list_revisions(self, item):
        """
        @see: Backend._list_revisions.__doc__
        """
        try:
            return self._item_revisions[item._item_id].keys()
        except KeyError:
            return []

    def _create_revision(self, item, revno):
        """
        @see: Backend._create_revision.__doc__
        """
        try:
            last_rev = max(self._item_revisions[item._item_id].iterkeys())
        except (ValueError, KeyError):
            last_rev = -1
        if revno != last_rev + 1:
            raise RevisionNumberMismatchError(("The latest revision of the item '%r' is %d, thus you cannot create revision number %d. "
                                               "The revision number must be latest_revision + 1.") % (item.name, last_rev, revno))
        try:
            if revno in self._item_revisions[item._item_id]:
                raise RevisionAlreadyExistsError("A Revision with the number %d already exists on the item %r" % (revno, item.name))
        except KeyError:
            pass  # First if-clause will raise an Exception if the Item has just
                  # been created (and not committed), because there is no entry in self._item_revisions yet. Thus, silenced.

        new_revision = self.NewRevision(item, revno)
        new_revision._revno = revno
        new_revision._data = StringIO.StringIO()
        return new_revision

    def _destroy_revision(self, revision):
        """
        @see: Backend._destroy_revision.__doc__
        """
        try:
            item_id = self._itemmap[revision.item.name]
            del self._item_revisions[item_id][revision.revno]
        except KeyError:
            # The revision has already been destroyed by someone else. No need to make our hands dirty.
            return

        # Remove the rev from history
        rev_history = [rev for rev in self._revision_history if (rev.item.name != revision.item.name or rev.revno != revision.revno)]
        self._revision_history = rev_history

    def _rename_item(self, item, newname):
        """
        @see: Backend._rename_item.__doc__
        """
        if self.has_item(newname):
            raise ItemAlreadyExistsError("Cannot rename Item %s to %s since there already is an Item with that name." % (item.name, newname))

        name = None
        for itemname, itemid in self._itemmap.iteritems():
            if itemid == item._item_id:
                name = itemname
                break
        assert name is not None

        copy_me = self._itemmap[name]
        self._itemmap[newname] = copy_me
        del self._itemmap[name]

    def _add_item_internally(self, item):
        """
        Given an item, store it persistently and initialize it. Please note
        that this method takes care of the internal counter we use to give each
        Item a unique ID.
        Not defined by superclass.

        @type item: Object of class Item.
        @param item: Item we want to add.
        """
        item._item_id = self._last_itemid
        self._itemmap[item.name] = item._item_id
        self._item_metadata[item._item_id] = {}
        self._item_revisions[item._item_id] = {}  # no revisions yet
        self._item_metadata_lock[item._item_id] = Lock()
        self._last_itemid += 1

    def _commit_item(self, revision):
        """
        @see: Backend._commit_item.__doc__
        """
        item = revision.item
        if item._item_id is None:
            if self.has_item(item.name):
                raise ItemAlreadyExistsError("You tried to commit an Item with the name %r, but there already is an Item with that name." % item.name)
            self._add_item_internally(item)
        elif self.has_item(item.name) and (revision.revno in self._item_revisions[item._item_id]):
            item._uncommitted_revision = None  # Discussion-Log: http://moinmo.in/MoinMoinChat/Logs/moin-dev/2008-06-20 around 17:27
            raise RevisionAlreadyExistsError("A Revision with the number %d already exists on the Item %r!" % (revision.revno, item.name))

        revision._data.seek(0)

        if revision._metadata is None:
            revision._metadata = {}
        revision._metadata['__timestamp'] = revision.timestamp
        self._item_revisions[item._item_id][revision.revno] = (revision._data.getvalue(), revision._metadata.copy())
        revision = item.get_revision(revision.revno)
        self._revision_history.append(revision)

    def _rollback_item(self, rev):
        """
        @see: Backend._rollback_item.__doc__
        """
        # Since we have no temporary files or other things to deal with in this backend,
        # we can just set the items uncommitted revision to None.
        pass

    def _change_item_metadata(self, item):
        """
        @see: Backend._change_item_metadata.__doc__
        """
        if item._item_id is None:
            # If this is the case it means that we operate on an Item that has not been
            # committed yet and thus we should not use a Lock in persistant storage.
            pass
        else:
            self._item_metadata_lock[item._item_id].acquire()

    def _publish_item_metadata(self, item):
        """
        @see: Backend._publish_item_metadata.__doc__
        """
        if item._item_id is None and self.has_item(item.name):
            raise  ItemAlreadyExistsError, "The Item whose metadata you tried to publish already exists."
        if item._item_id is None:
            # not committed yet, no locking, store item
            self._add_item_internally(item)
        else:
            self._item_metadata_lock[item._item_id].release()
        if item._metadata is not None:
            self._item_metadata[item._item_id] = item._metadata.copy()
        else:
            self._item_metadata[item._item_id] = {}

    def _read_revision_data(self, revision, chunksize):
        """
        @see: Backend._read_revision_data.__doc__
        """
        return revision._data.read(chunksize)

    def _write_revision_data(self, revision, data):
        """
        @see: Backend._write_revision_data.__doc__
        """
        revision._data.write(data)

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.

        @type item: Object of class Item.
        @param item: Item for which we want to get the metadata dict.
        @return: dict
        """
        try:
            return dict(self._item_metadata[item._item_id])
        except KeyError:  # The Item we are operating on has not been committed yet.
            return dict()

    def _get_revision_metadata(self, revision):
        """
        Load metadata for a given Revision, returns dict.

        @type revision: Object of subclass of Revision.
        @param revision: Revision for which we want to get the metadata dict.
        @return: dict
        """
        item = revision._item
        return self._item_revisions[item._item_id][revision.revno][1]

    def _seek_revision_data(self, revision, position, mode):
        """
        @see: Backend._seek_revision_data.__doc__
        """
        revision._data.seek(position, mode)

    def _tell_revision_data(self, revision):
        """
        @see: Backend._tell_revision_data.__doc__
        """
        return revision._data.tell()


# ------ The tracing backend

class TracingItem(Item):
    pass

class TracingNewRevision(NewRevision):
    pass

class TracingStoredRevision(StoredRevision):
    pass


class TracingBackend(MemoryBackend):
    """ Records every operation. When you are finished calling things, run get_code or get_func."""
    # XXX could use weakrefs to determine if objects are still alive and keep them alive according
    # to the sampled info in order to emulate scalability issues
    Item = TracingItem
    StoredRevision = TracingStoredRevision
    NewRevision = TracingNewRevision
    codebuffer = []

    def __init__(self, filename=None):
        MemoryBackend.__init__(self)
        self._backend = self # hehe, more uniform code :)
        self.filename = filename

    def log_expr(self, expr):
        self.codebuffer.append(expr)

    def get_code(self):
        return "\n".join(["def run(backend, got_exc=lambda x: None):", "    pass"] + self.codebuffer)

    def get_func(self):
        if self.filename:
            file(self.filename, "w").write(self.get_code())
        l = {}
        eval(compile(self.get_code(), self.filename or "not_on_disk", "exec"), l, l)
        return l["run"]

def _get_thingie_id(thingie, item):
    """ Generates a unique id for item depending on its class of objects. """
    if thingie == "backend":
        return "backend"
    return "%s_%i" % (thingie, id(item), )

def _retval_to_expr(retval):
    """ Determines whether we need to do an assignment and generates the assignment subexpr if necessary. """
    for thingie, klass in (("item", Item), ("rev", RevisionBase)):
        if isinstance(retval, klass):
            return _get_thingie_id(thingie, retval) + " = "
    return ""

def _get_thingie_wrapper(thingie):
    def wrap_thingie(func):
        def wrapper(*args, **kwargs):
            exc = None
            log = args[0]._backend.log_expr
            level = 4
            retval = None
            try:
                try:
                    retval = func(*args, **kwargs)
                except Exception, e:
                    exc = type(e).__name__ # yes, not very exact
                    log(" " * level + "try:")
                    level += 4
                    raise
            finally:
                log(" " * level + "%s%s.%s(*%s, **%s)" % (_retval_to_expr(retval),
                _get_thingie_id(thingie, args[0]), func.func_name, repr(args[1:]), repr(kwargs)))
                if exc:
                    level -= 4
                    log(" " * level + "except Exception, e:")
                    level += 4
                    log(" " * level + "if type(e).__name__ != %r:" % (exc, ))
                    level += 4
                    log(" " * level + "got_exc(e)")
            return retval
        return wrapper
    return wrap_thingie


wrap_rev = _get_thingie_wrapper("rev")
wrap_item = _get_thingie_wrapper("item")
wrap_be = _get_thingie_wrapper("backend")

def do_meta_patchery():
    for fromclass, toclass, wrappergen in ((MemoryBackend, TracingBackend, wrap_be), (Item, TracingItem, wrap_item),
                               (NewRevision, TracingNewRevision, wrap_rev), (StoredRevision, TracingStoredRevision, wrap_rev)):
        for name, func in fromclass.__dict__.iteritems():
            if not name.startswith("_") and hasattr(func, 'func_name'):
                setattr(toclass, name, wrappergen(func))
do_meta_patchery()

del do_meta_patchery, wrap_rev, wrap_item, wrap_be, _get_thingie_wrapper

