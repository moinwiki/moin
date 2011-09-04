# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2008-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Backend for moin 1.9 compatible filesystem data storage.

    This backend is needed because we need to be able to read existing data
    to convert them to the more powerful new backend(s).

    This backend is neither intended for nor capable of being used for production.

    Note: we do not support emulation of trashbin-like deletion, you have to
          choose a deleted_mode (see below) when creating a FSPageBackend.
"""


import os
from StringIO import StringIO
import hashlib

MAX_NAME_LEN = 1000 # max length of a page name, page+attach name, user name

from sqlalchemy import create_engine, MetaData, Table, Column, String, Unicode, Integer

try:
    from sqlalchemy.exc import IntegrityError
except ImportError:
    from sqlalchemy.exceptions import IntegrityError

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config
from MoinMoin.config import ACL, CONTENTTYPE, UUID, NAME, NAME_OLD, REVERTED_TO, \
                            ACTION, ADDRESS, HOSTNAME, USERID, MTIME, EXTRA, COMMENT, \
                            IS_SYSITEM, SYSITEM_VERSION, \
                            TAGS, SIZE, HASH_ALGORITHM
from MoinMoin.storage import Backend, Item, StoredRevision
from MoinMoin.storage.backends._fsutils import quoteWikinameFS, unquoteWikiname
from MoinMoin.storage.backends._flatutils import split_body
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError
from MoinMoin.util.mimetype import MimeType
from MoinMoin.util.crypto import make_uuid, UUID_LEN


DELETED_MODE_KEEP = 'keep'
DELETED_MODE_KILL = 'kill'

CONTENTTYPE_DEFAULT = u'text/plain'
CONTENTTYPE_MOINWIKI = u'text/x.moin.wiki'
FORMAT_TO_CONTENTTYPE = {
    'wiki': u'text/x.moin.wiki',
    'text/wiki': CONTENTTYPE_MOINWIKI,
    'text/moin-wiki': CONTENTTYPE_MOINWIKI,
    'creole': u'text/x.moin.creole',
    'text/creole': u'text/x.moin.creole',
    'rst': u'text/rst',
    'text/rst': u'text/rst',
    'plain': u'text/plain',
    'text/plain': u'text/plain',
}

class Index(object):
    """
    maintain mappings with names / old userid (for user profile items) / uuid
    """
    def __init__(self, path, username_unique=True):
        engine = create_engine('sqlite:///%s/index.db' % path, echo=False)
        metadata = MetaData()
        metadata.bind = engine
        self.users = Table('users', metadata,
                           Column('uuid', Unicode, index=True, unique=True),
                           Column('name', Unicode, index=True, unique=username_unique),
                           Column('old_id', String, index=True, unique=True),
                           Column('refcount', Integer), # reference count in edit-log
                     )
        self.content = Table('content', metadata,
                             Column('uuid', Unicode, index=True, unique=True),
                             Column('name', Unicode, index=True, unique=True),
                       )
        metadata.create_all()

    def close(self):
        engine = self.users.metadata.bind
        engine.dispose()

    def user_uuid(self, name='', old_id='', refcount=False):
        """
        Get uuid for user name, create a new uuid if we don't already have one.

        :param name: name of user (unicode)
        :param old_id: moin 1.x user id (str)
        """
        idx = self.users
        if old_id:
            results = idx.select(idx.c.old_id==old_id).execute()
        elif name:
            results = idx.select(idx.c.name==name).execute()
        else:
            raise ValueError("you need to give name or old_id")
        row = results.fetchone()
        results.close()
        if row is not None:
            uuid = row[idx.c.uuid]
            if refcount:
                refs = row[idx.c.refcount]
                refs += 1
                idx.update().where(idx.c.uuid==uuid).values(refcount=refs).execute()
        else:
            uuid = make_uuid()
            if not name:
                # if we don't have a name, we were called from EditLog with just a old_id
                # an no name - to avoid non-unique name, assign uuid also to name
                name = uuid
            try:
                refs = refcount and 1 or 0
                idx.insert().values(name=name, uuid=uuid, old_id=old_id, refcount=refs).execute()
            except IntegrityError as err:
                # input maybe has duplicate names in user profiles
                logging.warning("Multiple user profiles for name: %r" % name)
        return uuid

    def user_old_id(self, uuid):
        """
        Get old_id for some user with uuid <uuid>.

        :param name: uuid - uuid of user (str)
        """
        idx = self.users
        results = idx.select(idx.c.uuid==uuid).execute()
        row = results.fetchone()
        results.close()
        if row is not None:
            old_id = row[idx.c.old_id]
            return old_id

    def content_uuid(self, name):
        """
        Get uuid for a content name, create a new uuid if we don't already have one.

        :param name: name of content item (page or page/attachment, unicode)
        """
        idx = self.content
        results = idx.select(idx.c.name==name).execute()
        row = results.fetchone()
        results.close()
        if row is not None:
            uuid = row[idx.c.uuid]
            return uuid
        else:
            uuid = make_uuid()
            try:
                idx.insert().values(name=name, uuid=uuid).execute()
            except IntegrityError as err:
                # shouldn't happen
                logging.warning(str(err))
            return uuid


class FSPageBackend(Backend):
    """
    MoinMoin 1.9 compatible, read-only, "just for the migration" filesystem backend.

    Everything not needed for the migration will likely just raise a NotImplementedError.
    """
    def __init__(self, path, idx_path, syspages=False, deleted_mode=DELETED_MODE_KEEP,
                 default_markup=u'wiki',
                 item_category_regex=ur'(?P<all>Category(?P<key>(?!Template)\S+))'):
        """
        Initialise filesystem backend.

        :param path: storage path (data_dir)
        :param idx_path: path for index storage
        :param syspages: either False (not syspages) or revision number of syspages
        :param deleted_mode: 'kill' - just ignore deleted pages (pages with
                                      non-existing current revision) and their attachments
                                      as if they were not there.
                                      Non-deleted pages (pages with an existing current
                                      revision) that have non-current deleted revisions
                                      will be treated as for 'keep'.
                             'keep' - keep deleted pages as items with empty revisions,
                                      keep their attachments. (default)
        :param default_markup: used if a page has no #format line, moin 1.9's default
                               'wiki' and we also use this default here.
        """
        self._path = path
        self._syspages = syspages
        assert deleted_mode in (DELETED_MODE_KILL, DELETED_MODE_KEEP, )
        self.deleted_mode = deleted_mode
        self.format_default = default_markup
        self.item_category_regex = re.compile(item_category_regex, re.UNICODE)
        self.idx = Index(idx_path)

    def close(self):
        self.idx.close()

    def _get_item_path(self, name, *args):
        """
        Returns the full path to the page directory.
        """
        name = quoteWikinameFS(name)
        path = os.path.join(self._path, 'pages', name, *args)
        return path

    def _get_rev_path(self, itemname, revno):
        """
        Returns the full path to the revision's data file.

        Revno 0 from API will get translated into "00000001" filename.
        """
        return self._get_item_path(itemname, "revisions", "%08d" % (revno + 1))

    def _get_att_path(self, itemname, attachname):
        """
        Returns the full path to the attachment file.
        """
        return self._get_item_path(itemname, "attachments", attachname.encode('utf-8'))

    def _current_path(self, itemname):
        return self._get_item_path(itemname, "current")

    def has_item(self, itemname):
        return os.path.isfile(self._current_path(itemname))

    def iter_items_noindex(self):
        pages_dir = os.path.join(self._path, 'pages')
        for f in os.listdir(pages_dir):
            itemname = unquoteWikiname(f)
            try:
                item = FsPageItem(self, itemname)
            except NoSuchItemError:
                continue
            else:
                yield item
                for attachitem in item.iter_attachments():
                    yield attachitem

    iteritems = iter_items_noindex

    def get_item(self, itemname):
        try:
            # first try to get a page:
            return FsPageItem(self, itemname)
        except NoSuchItemError:
            # do a second try, interpreting it as attachment:
            return FsAttachmentItem(self, itemname)

    def _get_item_metadata(self, item):
        return item._fs_meta

    def _list_revisions(self, item):
        # we report ALL revision numbers:
        # - zero-based (because the new storage api works zero based)
        # - we even include deleted revisions' revnos
        return range(item._fs_current + 1)

    def _get_revision(self, item, revno):
        if isinstance(item, FsPageItem):
            return FsPageRevision(item, revno)
        elif isinstance(item, FsAttachmentItem):
            return FsAttachmentRevision(item, revno)
        else:
            raise

    def _get_revision_metadata(self, rev):
        return rev._fs_meta

    def _read_revision_data(self, rev, chunksize):
        if rev._fs_data_file is None:
            rev._fs_data_file = open(rev._fs_data_fname, 'rb') # XXX keeps file open as long as rev exists
        return rev._fs_data_file.read(chunksize)

    def _seek_revision_data(self, rev, position, mode):
        if rev._fs_data_file is None:
            rev._fs_data_file = open(rev._fs_data_fname, 'rb') # XXX keeps file open as long as rev exists
        return rev._fs_data_file.seek(position, mode)


# Specialized Items/Revisions

class FsPageItem(Item):
    """ A moin 1.9 filesystem item (page) """
    def __init__(self, backend, itemname):
        Item.__init__(self, backend, itemname)
        currentpath = self._backend._current_path(itemname)
        editlogpath = self._backend._get_item_path(itemname, 'edit-log')
        self._fs_meta = {} # 'current' is the only page metadata and handled elsewhere
        try:
            with open(currentpath, 'r') as f:
                current = int(f.read().strip()) - 1 # new api is 0-based, old is 1-based
        except (OSError, IOError):
            # no current file means no item
            raise NoSuchItemError("No such item, %r" % itemname)
        except ValueError:
            # we have a current file, but its content is damaged
            raise # TODO: current = determine_current(revdir, editlog)
        self._fs_current = current
        self._fs_editlog = EditLog(editlogpath, idx=backend.idx)
        self._syspages = backend._syspages
        if backend.deleted_mode == DELETED_MODE_KILL:
            try:
                FsPageRevision(self, current)
            except NoSuchRevisionError:
                raise NoSuchItemError('deleted_mode wants killing/ignoring of page %r and its attachments' % itemname)
        uuid = backend.idx.content_uuid(itemname)
        self.uuid = self._fs_meta[UUID] = uuid
        self._fs_meta[NAME] = itemname

    def iter_attachments(self):
        attachmentspath = self._backend._get_item_path(self.name, 'attachments')
        try:
            attachments = os.listdir(attachmentspath)
        except OSError:
            attachments = []
        for f in attachments:
            attachname = f.decode('utf-8')
            try:
                name = '%s/%s' % (self.name, attachname)
                item = FsAttachmentItem(self._backend, name)
            except NoSuchItemError:
                continue
            else:
                yield item


class FsPageRevision(StoredRevision):
    """ A moin 1.9 filesystem item revision (page, combines meta+data) """
    def __init__(self, item, revno):
        StoredRevision.__init__(self, item, revno)
        if revno == -1: # not used by converter, but nice to try a life wiki
            revno = item._fs_current
        backend = self._backend = item._backend
        revpath = backend._get_rev_path(item.name, revno)
        editlog = item._fs_editlog
        # we just read the page and parse it here, makes the rest of the code simpler:
        try:
            with codecs.open(revpath, 'r', config.charset) as f:
                content = f.read()
        except (IOError, OSError):
            if revno == item._fs_current and item._backend.deleted_mode == DELETED_MODE_KILL:
                raise NoSuchRevisionError('deleted_mode wants killing/ignoring')
            # handle deleted revisions (for all revnos with 0<=revno<=current) here
            # we prepare some values for the case we don't find a better value in edit-log:
            meta = {MTIME: -1, # fake, will get 0 in the end
                    NAME: item.name, # will get overwritten with name from edit-log
                                     # if we have an entry there
                   }
            try:
                previous_meta = FsPageRevision(item, revno-1)._fs_meta
                # if this page revision is deleted, we have no on-page metadata.
                # but some metadata is required, thus we have to copy it from the
                # (non-deleted) revision revno-1:
                for key in [ACL, NAME, CONTENTTYPE, MTIME, ]:
                    if key in previous_meta:
                        meta[key] = previous_meta[key]
            except NoSuchRevisionError:
                pass # should not happen
            meta[MTIME] += 1 # it is now either 0 or prev rev mtime + 1
            data = u''
            try:
                editlog_data = editlog.find_rev(revno)
            except KeyError:
                if 0 <= revno <= item._fs_current:
                    editlog_data = { # make something up
                        ACTION: u'SAVE/DELETE',
                    }
                else:
                    raise NoSuchRevisionError('Item %r has no revision %d (not even a deleted one)!' %
                            (item.name, revno))
        else:
            try:
                editlog_data = editlog.find_rev(revno)
            except KeyError:
                if 0 <= revno <= item._fs_current:
                    editlog_data = { # make something up
                        NAME: item.name,
                        MTIME: int(os.path.getmtime(revpath)),
                        ACTION: u'SAVE',
                    }
            meta, data = split_body(content)
        meta.update(editlog_data)
        format = meta.pop('format', backend.format_default)
        meta[CONTENTTYPE] = FORMAT_TO_CONTENTTYPE.get(format, CONTENTTYPE_DEFAULT)
        if item._syspages:
            meta[IS_SYSITEM] = True
            meta[SYSITEM_VERSION] = item._syspages
        data = self._process_data(meta, data)
        data = data.encode(config.charset)
        size, hash_name, hash_digest = hash_hexdigest(data)
        meta[hash_name] = hash_digest
        meta[SIZE] = size
        self._fs_meta = {}
        for k, v in meta.iteritems():
            if isinstance(v, list):
                v = tuple(v)
            self._fs_meta[k] = v
        self._fs_data_fname = None # "file" is already opened here:
        self._fs_data_file = StringIO(data)

        acl_line = self._fs_meta.get(ACL)
        if acl_line is not None:
            self._fs_meta[ACL] = regenerate_acl(acl_line, config.ACL_RIGHTS_CONTENTS)

    def _process_data(self, meta, data):
        """ In moin 1.x markup, not all metadata is stored in the page's header.
            E.g. categories are stored in the footer of the page content. For
            moin2, we extract that stuff from content and put it into metadata.
        """
        if meta[CONTENTTYPE] == CONTENTTYPE_MOINWIKI:
            data = process_categories(meta, data, self._backend.item_category_regex)
        return data


def process_categories(meta, data, item_category_regex):
    # process categories to tags
    # find last ---- in the data plus the categories below it
    m = re.search(r'\n\r?\s*-----*', data[::-1])
    if m:
        start = m.start()
        end = m.end()
        # categories are after the ---- line
        if start > 0:
            categories = data[-start:]
        else:
            categories = u''
        # remove the ---- line from the content
        data = data[:-end]
        if categories:
            # for CategoryFoo, group 'all' matches CategoryFoo, group 'key' matches just Foo
            # we use 'all' so we don't need to rename category items
            matches = list(item_category_regex.finditer(categories))
            if matches:
                tags = [m.group('all') for m in matches]
                meta.setdefault(TAGS, []).extend(tags)
                # remove everything between first and last category from the content
                start = matches[0].start()
                end = matches[-1].end()
                rest = categories[:start] + categories[end:]
                data += u'\r\n' + rest.lstrip()
        data = data.rstrip() + u'\r\n'
    return data


class FsAttachmentItem(Item):
    """ A moin 1.9 filesystem item (attachment) """
    def __init__(self, backend, name):
        Item.__init__(self, backend, name)
        try:
            itemname, attachname = name.rsplit('/')
        except ValueError: # no '/' in there
            raise NoSuchItemError("No such attachment item, %r" % name)
        editlogpath = self._backend._get_item_path(itemname, 'edit-log')
        self._fs_current = 0 # attachments only have 1 revision with revno 0
        self._fs_meta = {} # no attachment item level metadata
        self._fs_editlog = EditLog(editlogpath, idx=backend.idx)
        attachpath = self._backend._get_att_path(itemname, attachname)
        if not os.path.isfile(attachpath):
            # no attachment file means no item
            raise NoSuchItemError("No such attachment item, %r" % name)
        self._fs_attachname = attachname
        self._fs_attachpath = attachpath
        # fetch parent page's ACL as it protected the attachment also:
        try:
            parentpage = FsPageItem(backend, itemname)
            parent_current_rev = parentpage.get_revision(-1)
            acl = parent_current_rev._fs_meta.get(ACL)
        except (NoSuchItemError, NoSuchRevisionError):
            acl = None
        self._fs_parent_acl = acl
        self._syspages = backend._syspages
        uuid = backend.idx.content_uuid(name)
        self.uuid = self._fs_meta[UUID] = uuid
        self._fs_meta[NAME] = name

class FsAttachmentRevision(StoredRevision):
    """ A moin 1.9 filesystem item revision (attachment) """
    def __init__(self, item, revno):
        if revno != 0:
            raise NoSuchRevisionError('Item %r has no revision %d (attachments just have revno 0)!' %
                    (item.name, revno))
        StoredRevision.__init__(self, item, revno)
        attpath = item._fs_attachpath
        editlog = item._fs_editlog
        try:
            editlog_data = editlog.find_attach(item._fs_attachname)
        except KeyError:
            editlog_data = { # make something up
                MTIME: int(os.path.getmtime(attpath)),
                ACTION: u'SAVE',
            }
        meta = editlog_data
        # attachments in moin 1.9 were protected by their "parent" page's acl
        if item._fs_parent_acl is not None:
            meta[ACL] = item._fs_parent_acl # XXX not needed for acl_hierarchic
        meta[CONTENTTYPE] = unicode(MimeType(filename=item._fs_attachname).content_type())
        with open(attpath, 'rb') as f:
            size, hash_name, hash_digest = hash_hexdigest(f)
        meta[hash_name] = hash_digest
        meta[SIZE] = size
        if item._syspages:
            meta[IS_SYSITEM] = True
            meta[SYSITEM_VERSION] = item._syspages
        self._fs_meta = meta
        self._fs_data_fname = attpath
        self._fs_data_file = None


from fs19_logfile import LogFile


class EditLog(LogFile):
    """ Access the edit-log and return metadata as the new api wants it. """
    def __init__(self, filename, buffer_size=4096, idx=None):
        LogFile.__init__(self, filename, buffer_size)
        self._NUM_FIELDS = 9
        self.idx = idx

    def parser(self, line):
        """ Parse edit-log line into fields """
        fields = line.strip().split(u'\t')
        fields = (fields + [u''] * self._NUM_FIELDS)[:self._NUM_FIELDS]
        keys = (MTIME, '__rev', ACTION, NAME, ADDRESS, HOSTNAME, USERID, EXTRA, COMMENT)
        result = dict(zip(keys, fields))
        # do some conversions/cleanups/fallbacks:
        result[MTIME] = int(long(result[MTIME] or 0) / 1000000) # convert usecs to secs
        result['__rev'] = int(result['__rev']) - 1 # old storage is 1-based, we want 0-based
        result[NAME] = unquoteWikiname(result[NAME])
        action = result[ACTION]
        extra = result[EXTRA]
        if extra:
            if action.startswith('ATT'):
                result[NAME] += u'/' + extra # append filename to pagename
                # keep EXTRA for find_attach
            elif action == 'SAVE/RENAME':
                if extra:
                    result[NAME_OLD] = extra
                del result[EXTRA]
                result[ACTION] = u'RENAME'
            elif action == 'SAVE/REVERT':
                if extra:
                    result[REVERTED_TO] = int(extra)
                del result[EXTRA]
                result[ACTION] = u'REVERT'
        userid = result[USERID]
        if userid:
            result[USERID] = self.idx.user_uuid(old_id=userid, refcount=True)
        return result

    def find_rev(self, revno):
        """ Find metadata for some revno revision in the edit-log. """
        for meta in self:
            if meta['__rev'] == revno:
                break
        else:
            self.to_begin()
            raise KeyError
        del meta['__rev']
        meta = dict([(k, v) for k, v in meta.items() if v]) # remove keys with empty values
        if meta.get(ACTION) == u'SAVENEW':
            # replace SAVENEW with just SAVE
            meta[ACTION] = u'SAVE'
        return meta

    def find_attach(self, attachname):
        """ Find metadata for some attachment name in the edit-log. """
        for meta in self.reverse(): # use reverse iteration to get the latest upload's data
            if (meta['__rev'] == 99999998 and  # 99999999-1 because of 0-based
                meta[ACTION] == 'ATTNEW' and
                meta[EXTRA] == attachname):
                break
        else:
            self.to_end()
            raise KeyError
        del meta['__rev']
        del meta[EXTRA] #  we have full name in NAME
        meta[ACTION] = u'SAVE'
        meta = dict([(k, v) for k, v in meta.items() if v]) # remove keys with empty values
        return meta


from MoinMoin import security

def regenerate_acl(acl_string, acl_rights_valid):
    """ recreate ACL string to remove invalid rights """
    assert isinstance(acl_string, unicode)
    result = []
    for modifier, entries, rights in security.ACLStringIterator(acl_rights_valid, acl_string):
        if (entries, rights) == (['Default'], []):
            result.append("Default")
        else:
            result.append("%s%s:%s" % (
                          modifier,
                          u','.join(entries),
                          u','.join(rights) # iterator has removed invalid rights
                         ))
    result = u' '.join(result)
    logging.debug("regenerate_acl %r -> %r" % (acl_string, result))
    return result


import re, codecs
from MoinMoin import config

class FSUserBackend(Backend):
    """
    MoinMoin 1.9 compatible, read-only, "just for the migration" filesystem backend.

    Everything not needed for the migration will likely just raise a NotImplementedError.
    """
    def __init__(self, path, idx_path, kill_save=False):
        """
        Initialise filesystem backend.

        :param path: storage path (user_dir)
        :param idx_path: path for index storage
        :param data_path: storage path (data_dir) - only used for index storage
        """
        self._path = path
        if kill_save:
            # XXX dirty trick because this backend is read-only,
            # XXX to be able to use the wiki logged-in
            from MoinMoin.user import User
            User.save = lambda x: None # do nothing, we can't save
        self.idx = Index(idx_path)

    def _get_item_path(self, name, *args):
        """
        Returns the full path to the user profile.
        """
        path = os.path.join(self._path, name, *args)
        return path

    def has_item(self, itemname):
        return os.path.isfile(self._get_item_path(itemname))

    def iter_items_noindex(self):
        for old_id in os.listdir(self._path):
            try:
                item = FsUserItem(self, old_id=old_id)
            except NoSuchItemError:
                continue
            else:
                yield item

    iteritems = iter_items_noindex

    def get_item(self, itemname):
        return FsUserItem(self, itemname)

    def _get_item_metadata(self, item):
        return item._fs_meta

    def _list_revisions(self, item):
        # user items have no revisions (storing everything in item metadata)
        return []

    def _get_revision(self, item, revno):
        raise NoSuchRevisionError('Item %r has no revision %d (no revisions at all)!' %
                (item.name, revno))


# Specialized Items/Revisions

class FsUserItem(Item):
    """ A moin 1.9 filesystem item (user) """
    user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')

    def __init__(self, backend, itemname=None, old_id=None):
        if itemname is not None:
            # get_item calls us with a new itemname (uuid)
            uuid = str(itemname)
            old_id = backend.idx.user_old_id(uuid=uuid)
        if not self.user_re.match(old_id):
            raise NoSuchItemError("userid does not match user_re")
        Item.__init__(self, backend, itemname) # itemname might be None still
        try:
            meta = self._parse_userprofile(old_id)
        except (OSError, IOError):
            # no current file means no item
            raise NoSuchItemError("No such item, %r" % itemname)
        self._fs_meta = meta = self._process_usermeta(meta)
        if itemname is None:
            # iteritems calls us without itemname, just with old_id
            uuid = backend.idx.user_uuid(name=meta['name'], old_id=old_id)
            itemname = unicode(uuid)
            Item.__init__(self, backend, itemname) # XXX init again, with itemname
        self.uuid = meta[UUID] = uuid

    def _parse_userprofile(self, old_id):
        with codecs.open(self._backend._get_item_path(old_id), "r", config.charset) as meta_file:
            metadata = {}
            for line in meta_file:
                if line.startswith('#') or line.strip() == "":
                    continue
                key, value = line.strip().split('=', 1)
                # Decode list values
                if key.endswith('[]'):
                    key = key[:-2]
                    value = _decode_list(value)

                # Decode dict values
                elif key.endswith('{}'):
                    key = key[:-2]
                    value = _decode_dict(value)

                metadata[key] = value
        return metadata

    def _process_usermeta(self, metadata):
        # stuff we want to have stored as boolean:
        bool_defaults = [ # taken from cfg.checkbox_defaults
            ('show_comments', 'False'),
            ('edit_on_doubleclick', 'True'),
            ('want_trivial', 'False'),
            ('mailto_author', 'False'),
            ('disabled', 'False'),
        ]
        for key, default in bool_defaults:
            metadata[key] = metadata.get(key, default) in ['True', 'true', '1']

        # stuff we want to have stored as integer:
        int_defaults = [
            ('edit_rows', '0'),
        ]
        for key, default in int_defaults:
            metadata[key] = int(metadata.get(key, default))

        # rename last_saved to MTIME, int MTIME should be enough:
        metadata[MTIME] = int(float(metadata.get('last_saved', '0')))

        # rename subscribed_pages to subscribed_items
        metadata['subscribed_items'] = metadata.get('subscribed_pages', [])

        # convert bookmarks from usecs (and str) to secs (int)
        metadata['bookmarks'] = [(interwiki, int(long(bookmark)/1000000))
                                 for interwiki, bookmark in metadata.get('bookmarks', {}).items()]

        # stuff we want to get rid of:
        kill = ['real_language', # crap (use 'language')
                'wikiname_add_spaces', # crap magic (you get it like it is)
                'recoverpass_key', # user can recover again if needed
                'editor_default', # not used any more
                'editor_ui', # not used any more
                'external_target', # ancient, not used any more
                'passwd', # ancient, not used any more (use enc_passwd)
                'show_emoticons', # ancient, not used any more
                'show_fancy_diff', # kind of diff display now depends on mimetype
                'show_fancy_links', # not used any more (now link rendering depends on theme)
                'show_toolbar', # not used any more
                'show_topbottom', # crap
                'show_nonexist_qm', # crap, can be done by css
                'show_page_trail', # theme decides whether to show trail
                'remember_last_visit', # we show trail, user can click there
                'remember_me', # don't keep sessions open for a long time
                'subscribed_pages', # renamed to subscribed_items
                'edit_cols', # not used any more
                'jid', # no jabber support
                'tz_offset', # we have real timezone now
                'date_fmt', # not used any more
                'datetime_fmt', # not used any more
                'last_saved', # renamed to MTIME
                'email_subscribed_events', # XXX no support yet
                'jabber_subscribed_events', # XXX no support yet
               ]
        for key in kill:
            if key in metadata:
                del metadata[key]

        # finally, remove some empty values (that have empty defaults anyway or
        # make no sense when empty):
        empty_kill = ['aliasname', 'bookmarks', 'enc_password',
                      'language', 'css_url', 'email', ] # XXX check subscribed_items, quicklinks
        for key in empty_kill:
            if key in metadata and metadata[key] in [u'', tuple(), {}, [], ]:
                del metadata[key]

        return metadata


def _decode_list(line):
    """
    Decode list of items from user data file

    :param line: line containing list of items, encoded with _encode_list
    :rtype: list of unicode strings
    :returns: list of items in encoded in line
    """
    items = [item.strip() for item in line.split('\t')]
    items = [item for item in items if item]
    return tuple(items)

def _decode_dict(line):
    """
    Decode dict of key:value pairs from user data file

    :param line: line containing a dict, encoded with _encode_dict
    :rtype: dict
    :returns: dict  unicode:unicode items
    """
    items = [item.strip() for item in line.split('\t')]
    items = [item for item in items if item]
    items = [item.split(':', 1) for item in items]
    return dict(items)

def hash_hexdigest(content, bufsize=4096):
    size = 0
    hash = hashlib.new(HASH_ALGORITHM)
    if hasattr(content, "read"):
        while True:
            buf = content.read(bufsize)
            hash.update(buf)
            size += len(buf)
            if not buf:
                break
    elif isinstance(content, str):
        hash.update(content)
        size = len(content)
    else:
        raise ValueError("unsupported content object: %r" % content)
    return size, HASH_ALGORITHM, unicode(hash.hexdigest())

