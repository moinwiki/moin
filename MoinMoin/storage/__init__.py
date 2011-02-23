# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Backends - Storage API Definition.

    The storage API consists of the classes defined in this module. That is:
    Backend, Item, Revision, NewRevision and StoredRevision.

    A concrete backend implements the abstract methods defined by the API,
    but also uses concrete methods that have already been defined in this
    module.
    A backend is a collection of items. Examples for backends include SQL,
    mercurial or filesystem. All of those are means to store data.

    Items are the units you store within those backends. You can store content
    of arbitrary type in an item, e.g. text, images or even films.

    An item itself has revisions and metadata. For instance, you can use that
    to show a diff between two `versions` of a page, where the page "Foo" is
    represented by an item and the two versions are represented by two
    revisions of that item.

    Metadata is data that describes other data. An item has metadata. Each
    revision has metadata as well. E.g. "Which user created this revision?"
    would be something stored in the metadata of a revision, while "Who created
    this page in the first place?" would be answered by looking at the metadata
    of the first revision. Thus, an item basically is a collection of revisions
    which contain the content for the item. The last revision represents the most
    recent contents. A stored item can have metadata or revisions, or both.

    For normal operation, revision data and metadata are immutable as soon as the
    revision is committed to storage (by calling the commit() method on the item
    that holds the revision), thus making it a StoredRevision.
    Item metadata, on the other hand, as infrequently used as it may be, is mutable.
    Hence, it can only be modified under a read lock.

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg,
                2009-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os
import sys
import shutil

from MoinMoin import log
logging = log.getLogger(__name__)

from UserDict import DictMixin
from MoinMoin.storage.error import RevisionNumberMismatchError, AccessError, \
                                   BackendError, NoSuchItemError, \
                                   RevisionAlreadyExistsError, ItemAlreadyExistsError

# we need a specific hash algorithm to store hashes of revision data into meta
# data. meta[HASH_ALGORITHM] = hash(rev_data, HASH_ALGORITHM)
# some backends may use this also for other purposes.
HASH_ALGORITHM = 'sha1'

import hashlib


class Backend(object):
    """
    This class abstracts access to backends. If you want to write a specific
    backend, say a mercurial backend, you have to implement the methods below.
    A backend knows of its items and can perform several item related operations
    such as search_items, get_item, create_item, etc.
    """
    #
    # If you need to write a backend it is sufficient
    # to implement the methods of this class. That
    # way you don't *have to* implement the other classes
    # like Item and Revision as well. Though, if you want
    # to, you can do it as well.
    # Assuming my_item is instanceof(Item), when you call
    # my_item.create_revision(42), internally the
    # _create_revision() method of the item's backend is
    # invoked and the item passes itself as parameter.
    #
    def search_items(self, searchterm):
        """
        Takes a MoinMoin search term and returns an iterator (maybe empty) over
        matching item objects (NOT item names!).

        @type searchterm: MoinMoin search term
        @param searchterm: The term for which to search.
        @rtype: iterator of item objects
        """
        # Very simple implementation because we have no indexing
        # or anything like that. If you want to optimize this, override it.
        # Needs self.iteritems.
        for item in self.iteritems():
            searchterm.prepare()
            if searchterm.evaluate(item):
                yield item

    def get_item(self, itemname):
        """
        Returns item object or raises Exception if that item does not exist.

        When implementing this, don't rely on has_item unless you've overridden it.

        @type itemname: unicode
        @param itemname: The name of the item we want to get.
        @rtype: item object
        @raise NoSuchItemError: No item with name 'itemname' is known to this backend.
        """
        raise NotImplementedError()

    def has_item(self, itemname):
        """
        Override this method!

        This method is added for convenience. With it you don't need to try get_item
        and catch an exception that may be thrown if the item doesn't exist yet.

        @type itemname: unicode
        @param itemname: The name of the item of which we want to know whether it exists.
        @rtype: bool
        """
        try:
            self.get_item(itemname)
            return True
        except NoSuchItemError:
            return False

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that item already exists,
        raise an exception.

        @type itemname: unicode
        @param itemname: Name of the item we want to create.
        @rtype: item object
        @raise ItemAlreadyExistsError: The item you were trying to create already exists.
        """
        raise NotImplementedError()

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend (like the
        dict method).

        @rtype: iterator of item objects
        """
        raise NotImplementedError()

    def history(self, reverse=True):
        """
        Returns an iterator over ALL revisions of ALL items stored in the backend.

        If reverse is True (default), give history in reverse revision timestamp
        order, otherwise in revision timestamp order.

        Note: some functionality (e.g. completely cloning one storage into
              another) requires that the iterator goes over really every
              revision we have.

        @type reverse: bool
        @param reverse: Indicate whether the iterator should go in reverse order.
        @rtype: iterator of revision objects
        """
        # generic and slow history implementation
        revs = []
        for item in self.iteritems():
            for revno in item.list_revisions():
                rev = item.get_revision(revno)
                revs.append((rev.timestamp, rev.revno, item.name, ))
        revs.sort() # from oldest to newest
        if reverse:
            revs.reverse()
        for ts, revno, name in revs:
            item = self.get_item(name)
            yield item.get_revision(revno)

    def _get_revision(self, item, revno):
        """
        For a given item and revision number, return the corresponding revision
        of that item.
        Note: If you pass -1 as revno, this shall return the latest revision of the item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type revno: int
        @param revno: Indicate which revision is wanted precisely. If revno is
        -1, return the most recent revision.
        @rtype: Object of class Revision
        @raise NoSuchRevisionError: No revision with that revno was found on item.
        """
        raise NotImplementedError()

    def _list_revisions(self, item):
        """
        For a given item, return a list containing all revision numbers (as ints)
        of the revisions the item has. The list must be ordered, starting with
        the oldest revision number.
        Since we allow to totally destroy certain revisions, list_revisions does
        not need to return subsequent, but only monotone revision numbers.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: list of ints (possibly empty)
        """
        raise NotImplementedError()

    def _create_revision(self, item, revno):
        """
        Takes an item object and creates a new revision. Note that you need to pass
        a revision number for concurrency reasons. The revno passed must be
        greater than the revision number of the item's most recent revision.
        The newly created revision object is returned to the caller.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type revno: int
        @param revno: Indicate which revision we want to create.
        @precondition: item.get_revision(-1).revno < revno
        @return: Object of class Revision.
        @raise RevisionAlreadyExistsError: Raised if a revision with that number
        already exists on item.
        @raise RevisionNumberMismatchError: Raised if precondition is not
        fulfilled.
        """
        raise NotImplementedError()

    def _destroy_revision(self, revision):
        """
        Similarly to self._destroy_item. The given revision is completely destroyed.
        As this is an irreversible action, great care must be taken when performing it.

        In case the revision has already been destroyed by someone else (e.g. another
        process) this method should just pass silently as the job is already done.

        If the revision cannot be destroyed for technical reasons (e.g. missing permissions
        on disk), this method shall raise a CouldNotDestroyError.

        Note: Again, backends not capable of really erasing something should at the very
              least ignore the existence of the revision in question. (The only hint will
              be the gap in item.list_revisions().

        @type revision: Object of class StoredRevision
        @param revision: The revision we want to destroy completely.
        @raises CouldNotDestroyError: Raised in case the revision could not be destroyed.
        """
        raise NotImplementedError()

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception if the item you are trying to rename
        does not exist or if the newname is already chosen by another item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type newname: string
        @param newname: Name of item after this operation has succeeded.
        @precondition: self.has_item(newname) == False
        @postcondition: self.has_item(newname) == True
        @raises ItemAlreadyExistsError: Raised if an item with name 'newname'
        already exists.
        @return: None
        """
        raise NotImplementedError()

    def _commit_item(self, revision):
        """
        Commits the changes that have been done to a given item. That is, after you
        created a revision on that item and filled it with data you still need to
        commit() it. You need to pass the revision you want to commit. The item
        can be looked up by the revision's 'item' property.

        @type revision: Object of class NewRevision.
        @param revision: The revision we want to commit to  storage.
        @return: None
        """
        raise NotImplementedError()

    def _rollback_item(self, revision):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.

        @type revision: Object of class NewRevision.
        @param revision: The revision we want to roll back.
        @return: None
        """
        raise NotImplementedError()

    def _destroy_item(self, item):
        """
        Use this method carefully!

        This method attempts to completely *destroy* an item with all its revisions and
        metadata. After that, it will be impossible to access the item again via the
        storage API. This is very different from the deletion a user can perform on
        a wiki item, as such a deletion does not really delete anything from disk but
        just hides the former existence of the item. Such a deletion is undoable, while
        having destroyed an item is not.
        This also destroys all history related to the item. In particular, this also
        deletes all the item's revisions and they won't turn up in history any longer.

        In case the item has already been destroyed by someone else (e.g. another process)
        this method should just pass silently as the job is already done.

        If the item cannot be destroyed for technical reasons (e.g. missing permissions
        on disk), this method shall raise a CouldNotDestroyError.

        Note: Several backends (in particular those based on VCS) do not, by their nature,
              support erasing any content that has been put into them at some point.
              Those backends then need to emulate erasure as best they can. They should at
              least ignore the former existence of the item completely.
              A wiki admin must be aware that when using such a backend, he either needs
              to invoke an erasure (clone old, dirtied backend to new, fresh backend) script
              from time to time to get rid of the stuff, or not choose a backend of this
              kind (in case disk space is limited and large items are uploaded).

        @type item: Object of class Item
        @param item: The item we want to destroy
        @raises CouldNotDestroyError: Raised in case the revision could not be destroyed.
        @return: None
        """
        # XXX Should this perhaps return a bool indicating whether erasure was actually performed on disk or something like that?
        raise NotImplementedError()

    def _change_item_metadata(self, item):
        """
        This method is used to acquire a lock on an item. This is necessary to prevent
        side effects caused by concurrency.

        You need to call this method before altering the metadata of the item.
        E.g.:   item.change_metadata()  # Invokes this method
                item["metadata_key"] = "metadata_value"
                item.publish_metadata()

        As you can see, the lock acquired by this method is released by calling
        the publish_metadata() method on the item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @precondition: item not already locked
        @return: None
        """
        raise NotImplementedError()

    def _publish_item_metadata(self, item):
        """
        This method tries to release a lock on the given item and put the newly
        added Metadata of the item to storage.

        You need to call this method after altering the metadata of the item.
        E.g.:   item.change_metadata()
                item["metadata_key"] = "metadata_value"
                item.publish_metadata()  # Invokes this method

        The lock this method releases is acquired by the _change_metadata method.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @raise AssertionError: item was not locked XXX use more special exception
        @return: None
        """
        raise NotImplementedError()

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revision's data. By default, all
        data is read.

        @type revision: Object of class StoredRevision.
        @param revision: The revision on which we want to operate.
        @type chunksize: int
        @param chunksize: amount of bytes to be read at a time
        @return: string
        """
        raise NotImplementedError()

    def _write_revision_data(self, revision, data):
        """
        When this method is called, the passed data is written to the revision's data.

        @type revision: Object of class NewRevision.
        @param revision: The revision on which we want to operate.
        @type data: str
        @param data: The data to be written on the revision.
        @return: None
        """
        raise NotImplementedError()

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: dict of metadata key / value pairs.
        """
        raise NotImplementedError()

    def _get_revision_metadata(self, revision):
        """
        Load metadata for a given revision, returns dict.

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: dict of metadata key / value pairs.
        """
        raise NotImplementedError()

    def _get_revision_timestamp(self, revision):
        """
        Lazily load the revision's timestamp. If accessing it is cheap, it can
        be given as a parameter to StoredRevision instantiation instead.
        Return the timestamp (a long).

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: long
        """
        raise NotImplementedError()

    def _get_revision_size(self, revision):
        """
        Lazily access the revision's data size. This needs not be implemented
        if all StoredRevision objects are instantiated with the size= keyword
        parameter.

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: int
        """
        raise NotImplementedError()

    def _seek_revision_data(self, revision, position, mode):
        """
        Set the revision's cursor on the revision's data.

        @type revision: Object of StoredRevision.
        @param revision: The revision on which we want to operate.
        @type position: int
        @param position: Indicates where to position the cursor
        @type mode: int
        @param mode: 0 for 'absolute positioning', 1 to seek 'relatively to the
        current position', 2 to seek 'relative to the files end'.
        @return: None
        """
        raise NotImplementedError()

    def _tell_revision_data(self, revision):
        """
        Tell the revision's cursor's position on the revision's data.

        @type revision: Object of type StoredRevision.
        @param revision: The revision on which tell() was invoked.
        @return: int indicating the cursor's position.
        """
        raise NotImplementedError()

    # item copying
    def _copy_item_progress(self, verbose, st):
        if verbose:
            progress_char = dict(converts='.', skips='s', fails='F')
            sys.stdout.write(progress_char[st])

    def copy_item(self, item, verbose=False, name=None):
        def same_revision(rev1, rev2):
            if rev1.timestamp != rev2.timestamp:
                return False
            for k, v in rev1.iteritems():
                if rev2[k] != v:
                    return False
            if rev1.size != rev2.size:
                return False
            return True

        if name is None:
            name = item.name

        status = dict(converts={}, skips={}, fails={})
        revisions = item.list_revisions()

        try:
            new_item = self.get_item(name)
        except NoSuchItemError:
            new_item = self.create_item(name)

        # This only uses the metadata of the item that we clone.
        # Arguments for doing this:
        #   * If old stuff ends up in item after clone, that'd be counter intuitive
        #   * When caching some data from the latest rev in the item, we don't want the old stuff.
        new_item.change_metadata()
        for k, v in item.iteritems():
            new_item[k] = v
        new_item.publish_metadata()

        for revno in revisions:
            revision = item.get_revision(revno)

            try:
                new_rev = new_item.create_revision(revision.revno)
            except RevisionAlreadyExistsError:
                existing_revision = new_item.get_revision(revision.revno)
                st = same_revision(existing_revision, revision) and 'skips' or 'fails'
            else:
                for k, v in revision.iteritems():
                    new_rev[k] = v
                new_rev.timestamp = revision.timestamp
                shutil.copyfileobj(revision, new_rev)
                new_item.commit()
                st = 'converts'
            try:
                status[st][name].append(revision.revno)
            except KeyError:
                status[st][name] = [revision.revno]
            self._copy_item_progress(verbose, st)

        return status['converts'], status['skips'], status['fails']

    # cloning support
    def _clone_before(self, source, verbose):
        if verbose:
            # reopen stdout file descriptor with write mode
            # and 0 as the buffer size (unbuffered)
            sys.stdout = os.fdopen(os.dup(sys.stdout.fileno()), 'w', 0)
            sys.stdout.write("[converting %s to %s]: " % (source.__class__.__name__,
                                                          self.__class__.__name__, ))

    def _clone_after(self, source, verbose):
        if verbose:
            sys.stdout.write("\n")

    def clone(self, source, verbose=False, only_these=[]):
        """
        Create exact copy of source Backend with all the Items into THIS
        backend. If you don't want all items, you can give an item name list
        in only_these.

        Note: this is a generic implementation, you can maybe specialize it to
              make it faster in your backend implementation (esp. if creating
              new items is expensive).

        Return a tuple consisting of three dictionaries (Item name:Revision
        numbers list): converted, skipped and failed Items dictionary.
        """
        def item_generator(source, only_these):
            if only_these:
                for name in only_these:
                    try:
                        yield source.get_item(name)
                    except NoSuchItemError:
                        # TODO Find out why this fails sometimes.
                        #sys.stdout.write("Unable to copy %s\n" % itemname)
                        pass
            else:
                for item in source.iteritems():
                    yield item

        self._clone_before(source, verbose)

        converts, skips, fails = {}, {}, {}
        for item in item_generator(source, only_these):
            c, s, f = self.copy_item(item, verbose)
            converts.update(c)
            skips.update(s)
            fails.update(f)

        self._clone_after(source, verbose)
        return converts, skips, fails


class Item(object, DictMixin):
    """
    An item object collects the information of an item (e.g. a page) that is
    stored in persistent storage. It has metadata and revisions.
    An item object is just a proxy to the information stored in the backend.
    It doesn't necessarily live very long.

    Do NOT create instances of this class directly, but use backend.get_item
    or backend.create_item!
    """
    def __init__(self, backend, itemname):
        """
        Initialize an item. Memorize the backend to which it belongs.

        @type backend: Object of a subclass of Backend.
        @param backend: The backend that stores this item.
        @type itemname: unicode
        @param itemname: The name representing this item in the backend. Unique
        within the backend.
        """
        self._backend = backend
        self._name = itemname
        self._locked = False
        self._read_accessed = False
        self._metadata = None  # Will be loaded lazily upon first real access.
        self._uncommitted_revision = None

    def get_name(self):
        """
        name is a read-only property of this class.
        """
        return self._name

    name = property(get_name, doc="This is the name of this item. This attribute is read-only.")

    @property
    def next_revno(self):
        """
        The revno of the most recent committed revision + 1.
        I.e., the next revision's revno.
        """
        revs = self.list_revisions()
        try:
            return revs[-1] + 1
        except IndexError:
            # No revisions yet (empty sequence)
            return 0

    def __setitem__(self, key, value):
        """
        In order to access the item's metadata you can use the well-known dict-like
        semantics Python's dictionaries offer. If you want to set a value,
        my_item["key"] = "value" will do the trick. Note that keys must be of the
        type string (or unicode).
        Values must be of the type str, unicode or tuple, in which case every element
        of the tuple must be a string, unicode or tuple object.
        You must wrap write accesses to metadata in change_metadata/publish_metadata calls.
        Keys starting with two underscores are reserved and cannot be used.

        @type key: str or unicode
        @param key: The keyword that is used to look up the corresponding value.
        @type value: str, unicode, int, long, float, bool, complex or a nested tuple thereof.
        @param value: The value that is referenced by the keyword `key` in this
        specific item's metadata dict.
        """
        if not self._locked:
            raise AttributeError("Cannot write to unlocked metadata")
        if not isinstance(key, (str, unicode)):
            raise TypeError("Key must be string type")
        if key.startswith('__'):
            raise TypeError("Key must not begin with two underscores")
        check_value_type_is_valid(value)
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)
        self._metadata[key] = value

    def __delitem__(self, key):
        """
        Delete an item metadata key/value pair.

        @type key: str or unicode
        @param key: Key identifying a unique key/value pair in this item's metadata.
        @postcondition: self[key] raises KeyError
        """
        if not self._locked:
            raise AttributeError("Cannot write to unlocked metadata")
        if key.startswith('__'):
            raise KeyError(key)
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)
        del self._metadata[key]

    def __getitem__(self, key):
        """
        See __setitem__.__doc__ -- You may use my_item["key"] to get the corresponding
        metadata value. Note however, that the key you pass must be of type str or unicode.

        @type key: str or unicode
        @param key: The key refering to the value we want to return.
        @return self._metadata[key]
        """
        self._read_accessed = True
        if not isinstance(key, (unicode, str)):
            raise TypeError("key must be string type")
        if key.startswith('__'):
            raise KeyError(key)
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)

        return self._metadata[key]

    def keys(self):
        """
        This method returns a list of all metadata keys of this item (i.e., a list of Strings.)
        That allows using Python's `for mdkey in itemobj: do_something` syntax.

        @return: list of metadata keys not starting with two leading underscores
        """
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)

        return [key for key in self._metadata if not key.startswith("__")]

    def change_metadata(self):
        """
        @see: Backend._change_item_metadata.__doc__
        """
        if self._uncommitted_revision is not None:
            raise RuntimeError(("You tried to change the metadata of the item %r but there "
                                "are uncommitted revisions on that item. Commit first.") % (self.name))
        if self._read_accessed:
            raise AccessError("Cannot lock after reading metadata")

        self._backend._change_item_metadata(self)
        self._locked = True

    def publish_metadata(self):
        """
        @see: Backend._publish_item_metadata.__doc__
        """
        if not self._locked:
            raise AccessError("cannot publish without change_metadata")
        self._backend._publish_item_metadata(self)
        self._read_accessed = False
        self._locked = False

    def get_revision(self, revno):
        """
        @see: Backend._get_revision.__doc__
        """
        return self._backend._get_revision(self, revno)

    def list_revisions(self):
        """
        @see: Backend._list_revisions.__doc__
        """
        return self._backend._list_revisions(self)

    def rename(self, newname):
        """
        @see: Backend._rename_item.__doc__
        """
        if not isinstance(newname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(newname)))

        self._backend._rename_item(self, newname)
        self._name = newname

    def commit(self):
        """
        @see: Backend._commit_item.__doc__
        """
        rev = self._uncommitted_revision
        assert rev is not None
        rev[HASH_ALGORITHM] = unicode(rev._rev_hash.hexdigest())
        self._backend._commit_item(rev)
        self._uncommitted_revision = None

    def rollback(self):
        """
        @see: Backend._rollback_item.__doc__
        """
        self._backend._rollback_item(self._uncommitted_revision)
        self._uncommitted_revision = None

    def create_revision(self, revno):
        """
        @see: Backend._create_revision.__doc__

        Please note that we do not require the revnos to be subsequent, but they
        need to be monotonic. I.e., a sequence like 0, 1, 5, 9, 10 is ok, but
        neither 0, 1, 1, 2, 3 nor 0, 1, 3, 2, 9 are.
        This is done so as to allow functionality like unserializing a backend
        whose item's revisions have been subject to destroy().
        """
        if self._locked:
            raise RuntimeError(("You tried to create revision #%d on the item %r, but there "
                                "is unpublished metadata on that item. Publish first.") % (revno, self.name))
        current_revno = self.next_revno - 1
        if current_revno >= revno:
            raise RevisionNumberMismatchError("You cannot create a revision with revno %s. Your revno must be greater than " % revno + \
                                              "the item's last revision, which is %s." % current_revno)
        if self._uncommitted_revision is not None:
            return self._uncommitted_revision
        else:
            self._uncommitted_revision = self._backend._create_revision(self, revno)
            return self._uncommitted_revision

    def destroy(self):
        """
        @see: Backend._destroy_item.__doc__
        """
        return self._backend._destroy_item(self)


class Revision(object, DictMixin):
    """
    This class serves as superclass for StoredRevision and NewRevision.
    An object of either subclass represents a revision of an item. An item can have
    several revisions at a time, one being the most recent revision.
    This is a principle that is similar to the concepts used in Version Control
    Systems.

    Each revision object has a creation timestamp in the 'timestamp' property
    that defaults to None for newly created revisions in which case it will be
    assigned at commit() time. It is writable for use by converter backends, but
    care must be taken in that case to create monotone timestamps!
    This timestamp is also retrieved via the backend's history() method.
    """
    def __init__(self, item, revno, timestamp=None):
        """
        Initialize the revision.

        @type item: Object of class Item.
        @param item: The item to which this revision belongs.
        @type revno: int
        @param revno: The unique number identifying this revision on the item.
        @type timestamp: int
        @param timestamp: int representing the UNIX time this revision was
        created. (UNIX time: seconds since the epoch, i.e. 1st of January 1970, 00:00 UTC)
        """
        self._revno = revno
        self._item = item
        self._backend = item._backend
        self._metadata = None
        self._timestamp = timestamp

    def _get_item(self):
        return self._item

    item = property(_get_item)

    def get_revno(self):
        """
        Getter for the read-only revno property.
        """
        return self._revno

    revno = property(get_revno, doc=("This property stores the revno of the revision object. "
                                     "Only read-only access is allowed."))

    def _load_metadata(self):
        self._metadata = self._backend._get_revision_metadata(self)

    def __getitem__(self, key):
        """
        @see: Item.__getitem__.__doc__
        """
        if not isinstance(key, (unicode, str)):
            raise TypeError("key must be string type")
        if key.startswith('__'):
            raise KeyError(key)
        if self._metadata is None:
            self._load_metadata()

        return self._metadata[key]

    def keys(self):
        """
        @see: Item.keys.__doc__
        """
        if self._metadata is None:
            self._load_metadata()

        return [key for key in self._metadata if not key.startswith("__")]


class StoredRevision(Revision):
    """
    This is the brother of NewRevision. It allows reading data from a revision
    that has already been stored in storage. It doesn't allow data manipulation
    and can only be used for information retrieval.

    Do NOT create instances of this class directly, but use item.get_revision or
    one of the other methods intended for getting stored revisions.
    """
    def __init__(self, item, revno, timestamp=None, size=None):
        """
        Initialize the StoredRevision
        """
        Revision.__init__(self, item, revno, timestamp)
        self._size = size

    def _get_ts(self):
        if self._timestamp is None:
            self._timestamp = self._backend._get_revision_timestamp(self)
        return self._timestamp

    timestamp = property(_get_ts, doc="This property returns the creation timestamp of the revision")

    def _get_size(self):
        if self._size is None:
            self._size = self._backend._get_revision_size(self)
            assert self._size is not None

        return self._size

    size = property(_get_size, doc="Size of revision's data")

    def __setitem__(self, key, value):
        """
        Revision metadata cannot be altered, thus, we raise an Exception.
        """
        raise AttributeError("Metadata of already existing revisions may not be altered.")

    def __delitem__(self, key):
        """
        Revision metadata cannot be altered, thus, we raise an Exception.
        """
        raise AttributeError("Metadata of already existing revisions may not be altered.")

    def read(self, chunksize=-1):
        """
        @see: Backend._read_revision_data.__doc__
        """
        return self._backend._read_revision_data(self, chunksize)

    def seek(self, position, mode=0):
        """
        @see: StringIO.StringIO().seek.__doc__
        """
        self._backend._seek_revision_data(self, position, mode)

    def tell(self):
        """
        @see: StringIO.StringIO().tell.__doc__
        """
        return self._backend._tell_revision_data(self)

    def destroy(self):
        """
        @see: Backend._destroy_revision.__doc__
        """
        self._backend._destroy_revision(self)


class NewRevision(Revision):
    """
    This is basically the same as Revision but with mutable metadata and data properties.

    Do NOT create instances of this class directly, but use item.create_revision.
    """
    def __init__(self, item, revno):
        """
        Initialize the NewRevision
        """
        Revision.__init__(self, item, revno, None)
        self._metadata = {}
        self._size = 0
        self._rev_hash = hashlib.new(HASH_ALGORITHM)

    def _get_ts(self):
        return self._timestamp

    def _set_ts(self, ts):
        ts = long(ts)
        self._timestamp = ts

    timestamp = property(_get_ts, _set_ts, doc="This property accesses the creation timestamp of the revision")

    def _get_size(self):
        return self._size

    size = property(_get_size, doc="Size of data written so far")

    def __setitem__(self, key, value):
        """
        Internal method used for dict-like access to the NewRevisions metadata-dict.
        Keys starting with two underscores are reserved and cannot be used.

        @type key: str or unicode
        @param key: The keyword that is used to look up the corresponding value.
        @type value: str, unicode, int, long, float, bool, complex or a nested tuple thereof.
        @param value: The value that is referenced by the keyword `key` in this
        specific items metadata-dict.
        """
        if not isinstance(key, (str, unicode)):
            raise TypeError("Key must be string type")
        if key.startswith('__'):
            raise TypeError("Key must not begin with two underscores")
        check_value_type_is_valid(value)

        self._metadata[key] = value

    def __delitem__(self, key):
        if key.startswith('__'):
            raise KeyError(key)

        del self._metadata[key]

    def write(self, data):
        """
        @see: Backend._write_revision_data.__doc__
        """
        self._size += len(data)
        self._rev_hash.update(data)
        self._backend._write_revision_data(self, data)


# Little helper function:
def check_value_type_is_valid(value):
    """
    For metadata-values, we allow only immutable types, namely:
    str, unicode, bool, int, long, float, complex and tuple.
    Since tuples can contain other types, we need to check the types recursively.

    @type value: str, unicode, int, long, float, complex, tuple
    @param value: A value of which we want to know if it is a valid metadata value.
    @return: bool
    """
    accepted = (bool, str, unicode, int, long, float, complex)
    if isinstance(value, accepted):
        return True
    elif isinstance(value, tuple):
        for element in value:
            if not check_value_type_is_valid(element):
                raise TypeError("Value must be one of %s or a nested tuple thereof. Not %r" % (accepted, type(value)))
        else:
            return True

