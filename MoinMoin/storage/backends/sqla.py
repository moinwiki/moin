# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Backends - SQLAlchemy Backend

    This backend utilizes the power of SQLAlchemy.
    You can use it to store your wiki contents using any database supported by
    SQLAlchemy. This includes SQLite, PostgreSQL and MySQL.

    XXX Note that this backend is not currently ready for use! See the TODOs. XXX


    Talking to the DB
    =================

    In order to communicate with the database, we need to establish a connection
    by requesting a 'session'. `Session` is a class that was bound to the backend object.
    When we create an instance of it, we can persist our objects, modify or delete them.
    (Note that the SA docs suggest keeping the session class in the module scope. That
    does not work for us as we need to to be able to create multiple backend objects,
    each potentially bound to a different database. If the session was global in the module,
    all backends would maintain a connection to the database whose backend was created last.)
    Usually a session is created at the beginning of a request and disposed after the request
    has been processed. This is a bit difficult to realize as we are completely unaware of
    requests on the storage layer.
    Furthermore the backend may be used to store large amounts of data. In order to properly
    deal with such BLOBs, we split them manually into smaller chunks that we can 'stream'
    sequentially from and to the database. (Note that there is no such thing as a file-like
    read(n) API for our DBMSs and we don't want to read a large BLOB into memory all at once).
    It is also very important that we dispose of all sessions that we create properly and in
    a 'timely' manner, because the number of concurrent connections that are allowed for
    a database may be very limited (e.g., 5). A session is properly ended by invoking one of
    the following methods: session.commit(), session.rollback() or session.close().
    As some attributes on our mapped objects are loaded lazily, a the mapped object must
    be bound to a session obviously for the load operation to succeed. In order to accomplish
    that, we currently add the mapped objects to a session and close that session after the object
    has gone out of scope. This is a HACK, because we use __del__, which is very unreliable.
    The proper way to deal with this would be adding revision.close() (and perhaps even item.close?)
    to the storage API and free all resources that were acquired in that method. That of course
    means that we need to adjust all storage-related code and add the close() calls.


    TODO
    ====
    The following is a list of things that need to be done before this backend can be used productively
    (not including beta tests):

        * Data.read must be changed to operate on dynamically loaded chunks. I.e., the data._chunks must
          be set to lazy='dynamic', which will then be a query instead of a collection.
        * Find a proper solution for methods that issue many SQL queries. Especially search_items is
          difficult, as we cannot know what data will be needed in the subsequent processing of the items
          returned, which will result in more queries being issued. Eager loading is only a partial solution.
        * MetaData should definitely NOT simply be stored as a dict in a PickleType Column. Store that properly,
          perhaps in (a) seperate table(s).
        * Find out why RC lists an item that was just written below Trash/ as well. (Likely a UI bug.)
        * Add revision.close() (and perhaps item.close()?) to the storage API and make use of it.
          With the help of __del__, find all places that do not properly close connections. Do NOT rely on
          __del__. Use it only as a last resort to close connections.
        * Perhaps restructure the code. (Move methods that don't have to be on the Item/Revision classes
          into the backend, for example.)
        * Make sure the sketched approach is threadsafe for our purposes. Perhaps use the contextual session
          instead.
        * Currently there only is SQLARevision. Make sure that operations that are not allowed (such as modifying
          the data of an already stored revision) raise the appropriate exceptions.
"""


from threading import Lock

from sqlalchemy import create_engine, Column, Unicode, Integer, Binary, PickleType, ForeignKey
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
# Only used/needed for development/testing:
from sqlalchemy.pool import StaticPool

from MoinMoin.storage import Backend, Item, Revision, NewRevision, StoredRevision
from MoinMoin.storage.error import ItemAlreadyExistsError, NoSuchItemError, NoSuchRevisionError, \
                                   RevisionAlreadyExistsError, StorageError


Base = declarative_base()

NAME_LEN = 512


class SQLAlchemyBackend(Backend):
    """
    The actual SQLAlchemyBackend. Take note that the session class is bound to
    the individual backend it belongs to.
    """
    def __init__(self, db_uri=None, verbose=False):
        """
        :type db_uri: str
        :param db_uri: The database uri that we pass on to SQLAlchemy.
                       May contain user/password/host/port/etc.
        :type verbose: bool
        :param verbose: Verbosity setting. If set to True this will print all SQL queries
                        to the console.
        """
        if db_uri is None:
            # These are settings that apply only for development / testing only. The additional args are necessary
            # due to some limitations of the in-memory sqlite database.
            db_uri = 'sqlite:///:memory:'
            self.engine = create_engine(db_uri, poolclass=StaticPool, connect_args={'check_same_thread': False})
        else:
            self.engine = create_engine(db_uri, echo=verbose, echo_pool=verbose)

        # Our factory for sessions. Note: We do NOT define this module-level because then different SQLABackends
        # using different engines (potentially different databases) would all use the same Session object with the
        # same engine that the backend instance that was created last bound it to.
        # XXX Should this perhaps use the scoped/contextual session instead?
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Create the database schema (for all tables)
        SQLAItem.metadata.bind = self.engine
        SQLAItem.metadata.create_all()
        # {id : Lockobject} -- lock registry for item metadata locks
        self._item_metadata_lock = {}

    def has_item(self, itemname):
        """
        @see: Backend.has_item.__doc__
        """
        try:
            session = self.Session()
            session.query(SQLAItem).filter_by(_name=itemname).one()
            return True
        except NoResultFound:
            return False
        finally:
            # Since we simply return a bool, we can (and must) close the session here without problems.
            session.close()

    def get_item(self, itemname):
        """
        @see: Backend.get_item.__doc__
        """
        session = self.Session()
        # The following fails if not EXACTLY one column is found, i.e., it also fails
        # if MORE than one item is found, which should not happen since names should be
        # unique.
        try:
            # Query for the item that matches the given itemname.
            item = session.query(SQLAItem).filter_by(_name=itemname).one()
            # SQLA doesn't call __init__, so we need to take care of that.
            item.setup(self)
            # Maybe somebody already got an instance of this Item and thus there already is a Lock for that Item.
            if not item.id in self._item_metadata_lock:
                self._item_metadata_lock[item.id] = Lock()
            return item
        except NoResultFound:
            raise NoSuchItemError("The item '%s' could not be found." % itemname)
        finally:
            session.close()

    def create_item(self, itemname):
        """
        @see: Backend.create_item.__doc__
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        # This 'premature' check is ok since it may take some time until item.commit()
        # is invoked and only there can the database raise an IntegrityError if the
        # uniqueness-constraint for the item name is violated.
        if self.has_item(itemname):
            raise ItemAlreadyExistsError("An item with the name %s already exists." % itemname)

        item = SQLAItem(self, itemname)
        return item

    def history(self, reverse=True):
        """
        @see: Backend.history.__doc__
        """
        session = self.Session()
        col = SQLARevision.id
        if reverse:
            col = col.desc()
        for rev in session.query(SQLARevision).order_by(col).yield_per(1):
            # yield_per(1) says: Don't load them into memory all at once.
            rev.setup(self)
            yield rev
        session.close()

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).
        As iteritems() is used rather often while accessing *all* items in most cases,
        we preload them all at once and then just iterate over them, yielding each
        item individually to conform with the storage API.
        The benefit is that we do not issue a query for each individual item, but
        only a single query.

        @see: Backend.history.__doc__
        """
        session = self.Session()
        all_items = session.query(SQLAItem).all()
        session.close()
        for item in all_items:
            item.setup(self)
            yield item

    def _create_revision(self, item, revno):
        """
        @see: Backend._create_revision.__doc__
        """
        rev = SQLARevision(item, revno)
        # Add a session to the object here so it can flush the written data to the
        # database chunkwise. This is somewhat ugly.
        rev.session = self.Session()
        rev.session.add(rev)
        return rev

    def _rename_item(self, item, newname):
        """
        @see: Backend._rename_item.__doc__
        """
        if item.id is None:
            raise AssertionError("Item not yet committed to storage. Cannot be renamed.")

        session = self.Session()
        item = session.query(SQLAItem).get(item.id)
        item._name = newname
        # No need to add the item since the session took note that its name was changed
        # and so it's in session.dirty and will be changed when committed.
        try:
            session.commit()
        except IntegrityError:
            raise ItemAlreadyExistsError("Rename operation failed. There already is " + \
                                         "an item named '%s'." % newname)
        finally:
            session.close()

    def _commit_item(self, revision):
        """
        @see: Backend._commit_item.__doc__
        """
        item = revision.item
        session = revision.session

        # We need to distinguish between different types of uniqueness constraint violations.
        # That is why we flush the item first, then we flush the revision and finally we commit.
        # Flush would have failed if either of the two was already present (item with the same name
        # or revision with the same revno on that item.)
        try:
            # try to flush item if it's not already persisted
            if item.id is None:
                session.add(item)
                session.flush()
        except IntegrityError:
            raise ItemAlreadyExistsError("An item with that name already exists.")
        except DataError:
            raise StorageError("The item's name is too long for this backend. It must be less than %s." % NAME_LEN)
        else:
            # Flushing of item succeeded. That means we can try to flush the revision.
            # Close the item's data container and add potentially pending chunks.
            revision._data.close()
            session.add(revision)
            try:
                session.flush()
            except IntegrityError:
                raise RevisionAlreadyExistsError("A revision with revno %d already exists on the item." \
                                                  % (revision.revno))
            else:
                # Flushing of revision succeeded as well. All is fine. We can now commit()
                session.commit()
                # After committing, the Item has an id and we can create a metadata lock for it
                self._item_metadata_lock[item.id] = Lock()
        finally:
            session.close()


    def _rollback_item(self, revision):
        """
        @see: Backend._rollback_item.__doc__
        """
        session = revision.session
        session.rollback()

    def _change_item_metadata(self, item):
        """
        @see: Backend._change_item_metadata.__doc__
        """
        if item.id is None:
            # If this is the case it means that we operate on an Item that has not been
            # committed yet and thus we should not use a Lock in persistant storage.
            pass
        else:
            self._item_metadata_lock[item.id].acquire()

    def _publish_item_metadata(self, item):
        """
        @see: Backend._publish_item_metadata.__doc__
        """
        # XXX This should just be tried and the exception be caught
        if item.id is None and self.has_item(item.name):
            raise ItemAlreadyExistsError("The Item whose metadata you tried to publish already exists.")
        session = self.Session()
        session.add(item)
        session.commit()
        try:
            lock = self._item_metadata_lock[item.id]
        except KeyError:
            # Item hasn't been committed before publish, hence no lock.
            pass
        else:
            lock.release()

    def _get_item_metadata(self, item):
        """
        @see: Backend._get_item_metadata.__doc__
        """
        # When the item is restored from the db, it's _metadata should already
        # be populated. If not, it means there isn't any.
        return {}


class SQLAItem(Item, Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    # Since not all DBMSs support arbitrarily long item names, we must
    # impose a limit. SQLite will ignore it, PostgreSQL will raise DataError
    # and MySQL will simply truncate. Sweet.
    # For faster lookup, index the item name.
    _name = Column(Unicode(NAME_LEN), unique=True, index=True)
    _metadata = Column(PickleType)

    def __init__(self, backend, itemname):
        self._name = itemname
        self.setup(backend)

    def setup(self, backend):
        """
        This is different from __init__ as it may be also invoked explicitly
        when the object is returned from the database. We may as well call
        __init__ directly, but having a separate method for that makes it clearer.
        """
        self._backend = backend
        self._locked = False
        self._read_accessed = False
        self._uncommitted_revision = None

    @property
    def element_attrs(self):
        return dict(name=self._name)

    def list_revisions(self):
        """
        @see: Item.list_revisions.__doc__
        """
        # XXX Why does this not work?
        # return [rev.revno for rev in self._revisions if rev.id is not None]
        session = self._backend.Session()
        revisions = session.query(SQLARevision).filter(SQLARevision._item_id==self.id).all()
        revnos = [rev.revno for rev in revisions]
        session.close()
        return revnos

    def get_revision(self, revno):
        """
        @see: Item.get_revision.__doc__
        """
        try:
            session = self._backend.Session()
            if revno == -1:
                revnos = self.list_revisions()
                try:
                    # If there are no revisions we can list, then obviously we can't get the desired revision.
                    revno = revnos[-1]
                except IndexError:
                    raise NoResultFound
            rev = session.query(SQLARevision).filter(SQLARevision._item_id==self.id).filter(SQLARevision._revno==revno).one()
            rev.setup(self._backend)
            # Don't close the session here as it is needed for the revision to read the Data and access its attributes.
            # This should be changed.
            rev.session = session
            rev.session.add(rev)
            return rev
        except NoResultFound:
            raise NoSuchRevisionError("Item %s has no revision %d." % (self.name, revno))

    def destroy(self):
        """
        @see: Item.destroy.__doc__
        """
        session = self._backend.Session()
        session.delete(self)
        session.commit()


class Chunk(Base):
    """
    A chunk of data. This represents a piece of the BLOB we tried to save.
    It is stored in one row in the database and can hence be retrieved independently
    from the other chunks of the BLOB.
    """
    __tablename__ = 'rev_data_chunks'

    id = Column(Integer, primary_key=True)
    chunkno = Column(Integer)
    _container_id = Column(Integer, ForeignKey('rev_data.id'))

    # Maximum chunk size.
    chunksize = 64 * 1024
    _data = Column(Binary(chunksize))

    def __init__(self, chunkno, data=''):
        # We enumerate the chunks so as to keep track of their order.
        self.chunkno = chunkno
        assert len(data) <= self.chunksize
        self._data = data

    @property
    def data(self):
        """
        Since we store the chunk's data internally as Binary type, we
        get buffer objects back from the DB. We need to convert them
        to str in order to work with them.
        """
        return str(self._data)

    def write(self, data):
        """
        Write the given data to this chunk. If the data is longer than
        what we can store (perhaps we were already filled a bit or it's
        just too much data), we return the amount of bytes written.
        """
        if data:
            remaining = self.chunksize - len(self.data)
            data = data[:remaining]
            self._data += data
        #else:
        #   # if data is empty, we do not need to do anything!
        #   pass
        return len(data)


class Data(Base):
    """
    Data that is assembled from smaller chunks.
    Bookkeeping is done here.
    """
    __tablename__ = 'rev_data'

    id = Column(Integer, primary_key=True)
    # We need to use the following cascade to add/delete the chunks from the database, if
    # Data is added/deleted.
    _chunks = relation(Chunk, order_by=Chunk.id, cascade='save-update, delete, delete-orphan')
    _revision_id = Column(Integer, ForeignKey('revisions.id'))
    size = Column(Integer)

    def __init__(self):
        self.setup()
        self.size = 0

    # XXX use sqla reconstructor
    def setup(self):
        """
        @see: SQLAItem.setup.__doc__
        """
        self.chunkno = 0
        self._last_chunk = Chunk(self.chunkno)
        self.cursor_pos = 0

    def write(self, data):
        """
        The given data is split into chunks and stored in Chunk objects.
        Each chunk is 'filled' until it is full (i.e., Chunk.chunksize == len(Chunk.data)).
        Only the last chunk may not be filled completely.
        This does *only* support sequential writing of data, because otherwise
        we'd need to re-order potentially all chunks after the cursor position.

        :type data: str
        :param data: The data we want to split and write to the DB in chunks.
        """
        # XXX This currently relies on the autoflush feature of the session. It should ideally
        #     flush after every chunk.
        while data:
            written = self._last_chunk.write(data)
            if written:
                self.size += written
                data = data[written:]
            else:
                self.chunkno += 1
                self._chunks.append(self._last_chunk)
                self._last_chunk = Chunk(self.chunkno)

    def read(self, amount=None):
        """
        The given amount of data is read from the smaller chunks that are contained in this
        Data container. The caller is completely unaware of the existence of those chunks.

        Behaves like file-API's read().

        :type amount: int
        :param amount: amount of bytes we want to read.
        """
        chunksize = self._last_chunk.chunksize

        available = self.size - self.cursor_pos
        if available < 0:
            # cursor might be far beyond EOF, but that still just means 0
            available = 0

        if amount is None or amount < 0 or amount > available:
            amount = available

        chunkno_first, head_offset = divmod(self.cursor_pos, chunksize)
        chunkno_last, tail_offset = divmod(self.cursor_pos + amount, chunksize)

        if tail_offset == 0:
            # This handles multiple special cases:
            # any read that ends on a CHUNK boundary - we do not need to read
            # chunkno_last because there is no data in it that we need to read.
            # this includes the very special case of a 0 byte read at pos 0.
            # this includes also the special case of a read ending at EOF and
            # EOF being on a CHUNK boundary.
            # We optimize that to not read the unneeded chunk (for the EOF case
            # this chunk does not even exist),  but use all bytes up to the end
            # of the previous chunk (if there is a previous chunk).
            chunkno_last -= 1
            tail_offset = chunksize

        chunks = [chunk.data for chunk in self._chunks[chunkno_first:chunkno_last+1]]
        if chunks:
            # make sure that there is at least one chunk to operate on
            # if there is no chunk at all, we have empty data
            if chunkno_first != chunkno_last:
                # more than 1 chunk, head and tail in different chunks
                chunks[0] = chunks[0][head_offset:]
                chunks[-1] = chunks[-1][:tail_offset]
            else:
                # only 1 chunk with head and tail inside it
                chunks[0] = chunks[0][head_offset:tail_offset]
        data = "".join(chunks)
        assert len(data) == amount
        self.cursor_pos += amount
        return data

    def seek(self, pos, mode=0):
        """
        @see: StringIO.seek.__doc__
        """
        if mode == 0:
            if pos < 0:
                raise IOError("invalid argument")
            cursor = pos
        elif mode == 1:
            cursor = max(0, self.cursor_pos + pos)
        elif mode == 2:
            cursor = max(0, self.size + pos)
        self.cursor_pos = cursor

    def tell(self):
        """
        @see: StringIO.tell.__doc__
        """
        return self.cursor_pos

    def close(self):
        """
        Close the Data container. Append the last chunk.
        """
        self._chunks.append(self._last_chunk)


class SQLARevision(NewRevision, Base):
    """
    The SQLARevision. This is currently only based on NewRevision.
    It does NOT currently check whether the operation performed is valid.
    """
    __tablename__ = 'revisions'
    # Impose a UniqueConstraint so only one revision with a specific revno may exist on one item
    __table_args__ = (UniqueConstraint('_item_id', '_revno'), {})

    id = Column(Integer, primary_key=True)
    # We need to add/delete the Data container of this revision when the revision is added/deleted
    _data = relation(Data, uselist=False, lazy=False, cascade='save-update, delete, delete-orphan')
    _item_id = Column(Integer, ForeignKey('items.id'), index=True)
    # If the item is deleted, delete this revision as well.
    _item = relation(SQLAItem, backref=backref('_revisions', cascade='delete, delete-orphan', lazy=True), cascade='', uselist=False, lazy=False)
    _revno = Column(Integer, index=True)
    _metadata = Column(PickleType)

    def __init__(self, item, revno, *args, **kw):
        super(SQLARevision, self).__init__(item, revno, *args, **kw)
        self._revno = revno
        self.setup(item._backend)
        self._item = item

    def __del__(self):
        # XXX XXX XXX DO NOT RELY ON THIS
        try:
            self.session.close()
        except AttributeError:
            pass

    @property
    def element_attrs(self):
        return dict(revno=str(self._revno))

    def setup(self, backend):
        if self._data is None:
            self._data = Data()
        if self._metadata is None:
            self._metadata = {}
        self._data.setup()
        self._backend = backend

    def write(self, data):
        """
        Write the given amount of data.
        """
        self._data.write(data)
        self._size = self._data.size

    def read(self, amount=None):
        """
        Read the given amount of data.
        """
        return self._data.read(amount)

    def seek(self, pos, mode=0):
        """
        Seek to the given pos.
        """
        self._data.seek(pos, mode)

    def tell(self):
        """
        Return the current cursor pos.
        """
        return self._data.tell()

    def close(self):
        """
        Close all open sessions.
        """
        self.session.close()

    def __setitem__(self, key, value):
        NewRevision.__setitem__(self, key, value)

    def destroy(self):
        """
        @see: Backend.Revision.destroy.__doc__
        """
        session = self._backend.Session.object_session(self)
        if session is None:
            session = self._backend.Session()
        session.delete(self)
        session.commit()
