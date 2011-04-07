# Copyright: 2009 MoinMoin:ThomasWaldmann
# Copyright: 2009 MoinMoin:ReimarBauer
# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2009 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - misc. mimetype items

    While MoinMoin.storage cares for backend storage of items,
    this module cares for more high-level, frontend items,
    e.g. showing, editing, etc. of wiki items.
"""
# TODO: split this huge module into multiple ones after code has stabilized

import os, re, time, datetime, base64
import tarfile
import zipfile
import tempfile
from StringIO import StringIO

from MoinMoin.security.textcha import TextCha, TextChaizedForm, TextChaValid
from MoinMoin.util.forms import make_generator
from MoinMoin.util.mimetype import MimeType

try:
    import PIL
    from PIL import Image as PILImage
    from PIL.ImageChops import difference as PILdiff
except ImportError:
    PIL = None

from MoinMoin import log
logging = log.getLogger(__name__)

try:
    import json
except ImportError:
    import simplejson as json

from flask import current_app as app
from flask import g as flaskg

from flask import request, url_for, Response, abort, escape
from werkzeug import is_resource_modified
from jinja2 import Markup

from MoinMoin.i18n import _, L_, N_
from MoinMoin.themes import render_template
from MoinMoin import wikiutil, config, user
from MoinMoin.util.send_file import send_file
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError, \
                                   StorageError
from MoinMoin.config import UUID, NAME, NAME_OLD, MTIME, REVERTED_TO, ACL, \
                            IS_SYSITEM, SYSITEM_VERSION,  USERGROUP, SOMEDICT, \
                            MIMETYPE, SIZE, LANGUAGE, ITEMLINKS, ITEMTRANSCLUSIONS, \
                            TAGS, ACTION, ADDRESS, HOSTNAME, USERID, EXTRA, COMMENT, \
                            HASH_ALGORITHM

COLS = 80
ROWS_DATA = 20
ROWS_META = 10


class DummyRev(dict):
    """ if we have no stored Revision, we use this dummy """
    def __init__(self, item, mimetype):
        self[MIMETYPE] = mimetype
        self.item = item
        self.timestamp = 0
        self.revno = None
    def read(self, size=-1):
        return ''
    def seek(self, offset, whence=0):
        pass
    def tell(self):
        return 0


class DummyItem(object):
    """ if we have no stored Item, we use this dummy """
    def __init__(self, name):
        self.name = name
    def list_revisions(self):
        return [] # same as an empty Item


class Item(object):
    """ Highlevel (not storage) Item """
    @classmethod
    def create(cls, name=u'', mimetype=None, rev_no=None, item=None):
        if rev_no is None:
            rev_no = -1
        if mimetype is None:
            mimetype = 'application/x-nonexistent'

        try:
            if item is None:
                item = flaskg.storage.get_item(name)
            else:
                name = item.name
        except NoSuchItemError:
            logging.debug("No such item: %r" % name)
            item = DummyItem(name)
            rev = DummyRev(item, mimetype)
            logging.debug("Item %r, created dummy revision with mimetype %r" % (name, mimetype))
        else:
            logging.debug("Got item: %r" % name)
            try:
                rev = item.get_revision(rev_no)
            except NoSuchRevisionError:
                try:
                    rev = item.get_revision(-1) # fall back to current revision
                    # XXX add some message about invalid revision
                except NoSuchRevisionError:
                    logging.debug("Item %r has no revisions." % name)
                    rev = DummyRev(item, mimetype)
                    logging.debug("Item %r, created dummy revision with mimetype %r" % (name, mimetype))
            logging.debug("Got item %r, revision: %r" % (name, rev_no))
        mimetype = rev.get(MIMETYPE) or mimetype # XXX: Why do we need ... or ... ?
        logging.debug("Item %r, got mimetype %r from revision meta" % (name, mimetype))
        logging.debug("Item %r, rev meta dict: %r" % (name, dict(rev)))

        def _find_item_class(mimetype, BaseClass, best_match_len=-1):
            #logging.debug("_find_item_class(%r,%r,%r)" % (mimetype, BaseClass, best_match_len))
            Class = None
            for ItemClass in BaseClass.__subclasses__():
                for supported_mimetype in ItemClass.supported_mimetypes:
                    if mimetype.startswith(supported_mimetype):
                        match_len = len(supported_mimetype)
                        if match_len > best_match_len:
                            best_match_len = match_len
                            Class = ItemClass
                            #logging.debug("_find_item_class: new best match: %r by %r)" % (supported_mimetype, ItemClass))
                best_match_len, better_Class = _find_item_class(mimetype, ItemClass, best_match_len)
                if better_Class:
                    Class = better_Class
            return best_match_len, Class

        ItemClass = _find_item_class(mimetype, cls)[1]
        logging.debug("ItemClass %r handles %r" % (ItemClass, mimetype))
        return ItemClass(name=name, rev=rev, mimetype=mimetype)

    def __init__(self, name, rev=None, mimetype=None):
        self.name = name
        self.rev = rev
        self.mimetype = mimetype

    def get_meta(self):
        return self.rev or {}
    meta = property(fget=get_meta)

    def _render_meta(self):
        # override this in child classes
        return ''

    def feed_input_conv(self):
        return self.name

    def internal_representation(self, converters=['smiley', 'link']):
        """
        Return the internal representation of a document using a DOM Tree
        """
        flaskg.clock.start('conv_in_dom')
        hash_name = HASH_ALGORITHM
        hash_hexdigest = self.rev.get(hash_name)
        if hash_hexdigest:
            cid = wikiutil.cache_key(usage="internal_representation",
                                     hash_name=hash_name,
                                     hash_hexdigest=hash_hexdigest)
            doc = app.cache.get(cid)
        else:
            # likely a non-existing item
            doc = cid = None
        if doc is None:
            # We will see if we can perform the conversion:
            # FROM_mimetype --> DOM
            # if so we perform the transformation, otherwise we don't
            from MoinMoin.converter import default_registry as reg
            from MoinMoin.util.iri import Iri
            from MoinMoin.util.mime import Type, type_moin_document
            from MoinMoin.util.tree import moin_page, xlink
            input_conv = reg.get(Type(self.mimetype), type_moin_document)
            if not input_conv:
                raise TypeError("We cannot handle the conversion from %s to the DOM tree" % self.mimetype)
            smiley_conv = reg.get(type_moin_document, type_moin_document,
                    icon='smiley')

            # We can process the conversion
            links = Iri(scheme='wiki', authority='', path='/' + self.name)
            input = self.feed_input_conv()
            doc = input_conv(input)
            # XXX is the following assuming that the top element of the doc tree
            # is a moin_page.page element? if yes, this is the wrong place to do that
            # as not every doc will have that element (e.g. for images, we just get
            # moin_page.object, for a tar item, we get a moin_page.table):
            doc.set(moin_page.page_href, unicode(links))
            for conv in converters:
                if conv == 'smiley':
                    doc = smiley_conv(doc)
            if cid:
                app.cache.set(cid, doc)
        flaskg.clock.stop('conv_in_dom')
        return doc

    def _expand_document(self, doc):
        from MoinMoin.converter import default_registry as reg
        from MoinMoin.util.iri import Iri
        from MoinMoin.util.mime import type_moin_document
        include_conv = reg.get(type_moin_document, type_moin_document, includes='expandall')
        macro_conv = reg.get(type_moin_document, type_moin_document, macros='expandall')
        link_conv = reg.get(type_moin_document, type_moin_document, links='extern',
                url_root=Iri(request.url_root))
        flaskg.clock.start('conv_include')
        doc = include_conv(doc)
        flaskg.clock.stop('conv_include')
        flaskg.clock.start('conv_macro')
        doc = macro_conv(doc)
        flaskg.clock.stop('conv_macro')
        flaskg.clock.start('conv_link')
        doc = link_conv(doc)
        flaskg.clock.stop('conv_link')
        return doc

    def _render_data(self):
        from MoinMoin.converter import default_registry as reg
        from MoinMoin.util.mime import Type, type_moin_document
        from MoinMoin.util.tree import html
        include_conv = reg.get(type_moin_document, type_moin_document, includes='expandall')
        macro_conv = reg.get(type_moin_document, type_moin_document, macros='expandall')
        # TODO: Real output format
        html_conv = reg.get(type_moin_document, Type('application/x-xhtml-moin-page'))
        doc = self.internal_representation()
        doc = self._expand_document(doc)
        flaskg.clock.start('conv_dom_html')
        doc = html_conv(doc)
        flaskg.clock.stop('conv_dom_html')

        from array import array
        out = array('u')
        flaskg.clock.start('conv_serialize')
        doc.write(out.fromunicode, namespaces={html.namespace: ''}, method='xml')
        out = out.tounicode()
        flaskg.clock.stop('conv_serialize')
        return out

    def _render_data_xml(self, converters):
        from MoinMoin.util.tree import moin_page, xlink, html
        doc = self.internal_representation(converters)

        from array import array
        out = array('u')
        doc.write(out.fromunicode,
                  namespaces={moin_page.namespace: '',
                              xlink.namespace: 'xlink',
                              html.namespace: 'html',
                             },
                  method='xml')
        return out.tounicode()

    def _do_modify_show_templates(self):
        # call this if the item is still empty
        rev_nos = []
        item_templates = self.get_templates(self.mimetype)
        return render_template('modify_show_template_selection.html',
                               item_name=self.name,
                               rev=self.rev,
                               mimetype=self.mimetype,
                               templates=item_templates,
                               first_rev_no=rev_nos and rev_nos[0],
                               last_rev_no=rev_nos and rev_nos[-1],
                               meta_rendered='',
                               data_rendered='',
                              )

    def meta_filter(self, meta):
        """ kill metadata entries that we set automatically when saving """
        kill_keys = [# shall not get copied from old rev to new rev
                     SYSITEM_VERSION,
                     NAME_OLD,
                     # are automatically implanted when saving
                     NAME,
                     UUID,
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

    def get_data(self):
        return '' # TODO create a better method for binary stuff
    data = property(fget=get_data)

    def _write_stream(self, content, new_rev, bufsize=8192):
        if hasattr(content, "read"):
            while True:
                buf = content.read(bufsize)
                if not buf:
                    break
                new_rev.write(buf)
        elif isinstance(content, str):
            new_rev.write(content)
        else:
            raise StorageError("unsupported content object: %r" % content)

    def copy(self, name, comment=u''):
        """
        copy this item to item <name>
        """
        old_item = self.rev.item
        flaskg.storage.copy_item(old_item, name=name)
        current_rev = old_item.get_revision(-1)
        # we just create a new revision with almost same meta/data to show up on RC
        self._save(current_rev, current_rev, name=name, action=u'COPY', comment=comment)

    def _rename(self, name, comment, action):
        self.rev.item.rename(name)
        self._save(self.meta, self.data, name=name, action=action, comment=comment)

    def rename(self, name, comment=u''):
        """
        rename this item to item <name>
        """
        return self._rename(name, comment, action=u'RENAME')

    def delete(self, comment=u''):
        """
        delete this item by moving it to the trashbin
        """
        trash_prefix = u'Trash/' # XXX move to config
        now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        # make trash name unique by including timestamp:
        trashname = u'%s%s (%s UTC)' % (trash_prefix, self.name, now)
        return self._rename(trashname, comment, action=u'TRASH')

    def revert(self):
        # called from revert UI/POST
        comment = request.form.get('comment')
        self._save(self.meta, self.data, action=u'REVERT', comment=comment)

    def destroy(self, comment=u'', destroy_item=False):
        # called from destroy UI/POST
        if destroy_item:
            # destroy complete item with all revisions, metadata, etc.
            self.rev.item.destroy()
        else:
            # just destroy this revision
            self.rev.destroy()

    def modify(self):
        # called from modify UI/POST
        data_file = request.files.get('data_file')
        mimetype = request.values.get('mimetype', 'text/plain')
        if data_file and data_file.filename:
            # user selected a file to upload
            data = data_file.stream
            mimetype = MimeType(filename=data_file.filename).mime_type()
        else:
            # take text from textarea
            data = request.form.get('data_text', '')
            if data:
                data = self.data_form_to_internal(data)
                data = self.data_internal_to_storage(data)
                mimetype = 'text/plain'
            else:
                data = '' # could've been u'' also!
                mimetype = None
        meta_text = request.form.get('meta_text', '')
        meta = self.meta_text_to_dict(meta_text)
        comment = request.form.get('comment')
        self._save(meta, data, mimetype=mimetype, comment=comment)

    def _save(self, meta, data, name=None, action=u'SAVE', mimetype=None, comment=u''):
        if name is None:
            name = self.name
        backend = flaskg.storage
        try:
            storage_item = backend.get_item(name)
        except NoSuchItemError:
            storage_item = backend.create_item(name)
        try:
            currentrev = storage_item.get_revision(-1)
            rev_no = currentrev.revno
            if mimetype is None:
                # if we didn't get mimetype info, thus reusing the one from current rev:
                mimetype = currentrev.get(MIMETYPE)
        except NoSuchRevisionError:
            rev_no = -1
        newrev = storage_item.create_revision(rev_no + 1)
        for k, v in meta.iteritems():
            # TODO Put metadata into newrev here for now. There should be a safer way
            #      of input for this.
            newrev[k] = v

        # we store the previous (if different) and current item name into revision metadata
        # this is useful for rename history and backends that use item uids internally
        oldname = meta.get(NAME)
        if oldname and oldname != name:
            newrev[NAME_OLD] = oldname
        newrev[NAME] = name

        self._write_stream(data, newrev)
        timestamp = time.time()
        # XXX if meta is from old revision, and user did not give a non-empty
        # XXX comment, re-using the old rev's comment is wrong behaviour:
        comment = unicode(comment or meta.get(COMMENT, ''))
        if comment:
            newrev[COMMENT] = comment
        # allow override by form- / qs-given mimetype:
        mimetype = request.values.get('mimetype', mimetype)
        # allow override by give metadata:
        assert mimetype is not None
        newrev[MIMETYPE] = unicode(meta.get(MIMETYPE, mimetype))
        newrev[ACTION] = unicode(action)
        self.before_revision_commit(newrev, data)
        storage_item.commit()
        # XXX Event ?

    def before_revision_commit(self, newrev, data):
        """
        hook that can be used to add more meta data to a revision before
        it is committed.

        :param newrev: new (still uncommitted) revision - modify as wanted
        :param data: either str or open file (we can avoid having to read/seek
                     rev's data with this)
        """
        remote_addr = request.remote_addr
        if remote_addr:
            if app.cfg.log_remote_addr:
                newrev[ADDRESS] = unicode(remote_addr)
                hostname = wikiutil.get_hostname(remote_addr)
                if hostname:
                    newrev[HOSTNAME] = hostname
        if flaskg.user.valid:
            newrev[USERID] = unicode(flaskg.user.id)

    def search_items(self, term=None):
        """ search items matching the term or,
            if term is None, return all items
        """
        if term:
            backend_items = flaskg.storage.search_items(term)
        else:
            # special case: we just want all items
            backend_items = flaskg.storage.iteritems()
        for item in backend_items:
            yield Item.create(item=item)

    list_items = search_items  # just for cosmetics

    def count_items(self, term=None):
        """
        Return item count for matching items. See search_items() for details.
        """
        count = 0
        # we intentionally use a loop to avoid creating a list with all item objects:
        for item in self.list_items(term):
            count += 1
        return count

    def get_index(self):
        """ create an index of sub items of this item """
        import re
        from MoinMoin.storage.terms import NameRE

        if self.name:
            prefix = self.name + u'/'
        else:
            # trick: an item of empty name can be considered as "virtual root item",
            # that has all wiki items as sub items
            prefix = u''
        sub_item_re = u"^%s.*" % re.escape(prefix)
        regex = re.compile(sub_item_re, re.UNICODE)

        item_iterator = self.search_items(NameRE(regex))

        # We only want the sub-item part of the item names, not the whole item objects.
        prefix_len = len(prefix)
        items = [(item.name, item.name[prefix_len:], item.meta.get(MIMETYPE))
                 for item in item_iterator]
        return sorted(items)

    def flat_index(self):
        index = self.get_index()
        index = [(fullname, relname, mimetype)
                 for fullname, relname, mimetype in index
                 if u'/' not in relname]
        return index

    index_template = 'index.html'


class NonExistent(Item):
    supported_mimetypes = ['application/x-nonexistent']
    mimetype_groups = [
        ('markup text items', [
            ('text/x.moin.wiki', 'Wiki (MoinMoin)'),
            ('text/x.moin.creole', 'Wiki (Creole)'),
            ('text/x-mediawiki', 'Wiki (MediaWiki)'),
            ('text/x-rst', 'ReST'),
            ('application/docbook+xml', 'DocBook'),
            ('text/html', 'HTML'),
        ]),
        ('other text items', [
            ('text/plain', 'plain text'),
            ('text/x-diff', 'diff/patch'),
            ('text/x-python', 'python code'),
            ('text/csv', 'csv'),
            ('text/x-irclog', 'IRC log'),
        ]),
        ('image items', [
            ('image/jpeg', 'JPEG'),
            ('image/png', 'PNG'),
            ('image/svg+xml', 'SVG'),
        ]),
        ('audio items', [
            ('audio/wave', 'WAV'),
            ('audio/ogg', 'OGG'),
            ('audio/mpeg', 'MP3'),
            ('audio/webm', 'WebM'),
        ]),
        ('video items', [
            ('video/ogg', 'OGG'),
            ('video/webm', 'WebM'),
            ('video/mp4', 'MP4'),
        ]),
        ('drawing items', [
            ('application/x-twikidraw', 'TDRAW'),
            ('application/x-anywikidraw', 'ADRAW'),
            ('application/x-svgdraw', 'SVGDRAW'),
        ]),

        ('other items', [
            ('application/pdf', 'PDF'),
            ('application/zip', 'ZIP'),
            ('application/x-tar', 'TAR'),
            ('application/x-gtar', 'TGZ'),
            ('application/octet-stream', 'binary file'),
        ]),
    ]

    def do_get(self):
        abort(404)

    def _convert(self):
        abort(404)

    def do_modify(self, template_name):
        # XXX think about and add item template support
        return render_template('modify_show_type_selection.html',
                               item_name=self.name,
                               mimetype_groups=self.mimetype_groups,
                              )


class Binary(Item):
    """ An arbitrary binary item, fallback class for every item mimetype. """
    supported_mimetypes = [''] # fallback, because every mimetype starts with ''

    modify_help = """\
There is no help, you're doomed!
"""

    template = "modify_binary.html"

    # XXX reads item rev data into memory!
    def get_data(self):
        if self.rev is not None:
            return self.rev.read()
        else:
            return ''
    data = property(fget=get_data)

    def _render_meta(self):
        return "<pre>%s</pre>" % escape(self.meta_dict_to_text(self.meta, use_filter=False))

    def get_templates(self, mimetype=None):
        """ create a list of templates (for some specific mimetype) """
        from MoinMoin.storage.terms import AND, LastRevisionMetaDataMatch
        term = LastRevisionMetaDataMatch(TAGS, ['template']) # XXX there might be other tags
        if mimetype:
            term = AND(term, LastRevisionMetaDataMatch(MIMETYPE, mimetype))
        item_iterator = self.search_items(term)
        items = [item.name for item in item_iterator]
        return sorted(items)

    def do_modify(self, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        form = TextChaizedForm.from_defaults()
        TextCha(form).amend_form()
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=ROWS_META, cols=COLS,
                               revno=0,
                               meta_text=self.meta_dict_to_text(self.meta),
                               help=self.modify_help,
                               form=form,
                               gen=make_generator(),
                              )

    copy_template = 'copy.html'
    delete_template = 'delete.html'
    destroy_template = 'destroy.html'
    diff_template = 'diff.html'
    rename_template = 'rename.html'
    revert_template = 'revert.html'

    def _render_data_diff(self, oldrev, newrev):
        hash_name = HASH_ALGORITHM
        if oldrev[hash_name] == newrev[hash_name]:
            return _("The items have the same data hash code (that means they very likely have the same data).")
        else:
            return _("The items have different data.")

    _render_data_diff_text = _render_data_diff
    _render_data_diff_raw = _render_data_diff

    def _convert(self):
        return _("Impossible to convert the data to the mimetype: %(mimetype)s",
                 mimetype=request.values.get('mimetype'))

    def do_get(self):
        hash = self.rev.get(HASH_ALGORITHM)
        if is_resource_modified(request.environ, hash): # use hash as etag
            return self._do_get_modified(hash)
        else:
            return Response(status=304)

    def _do_get_modified(self, hash):
        member = request.values.get('member')
        return self._do_get(hash, member)

    def _do_get(self, hash, member=None):
        filename = None
        if member: # content = file contained within a archive item revision
            path, filename = os.path.split(member)
            mt = MimeType(filename=filename)
            content_disposition = mt.content_disposition(app.cfg)
            content_type = mt.content_type()
            content_length = None
            file_to_send = self.get_member(member)
        else: # content = item revision
            rev = self.rev
            try:
                mimestr = rev[MIMETYPE]
            except KeyError:
                mimestr = mimetypes.guess_type(rev.item.name)[0]
            mt = MimeType(mimestr=mimestr)
            content_disposition = mt.content_disposition(app.cfg)
            content_type = mt.content_type()
            content_length = rev[SIZE]
            file_to_send = rev

        # TODO: handle content_disposition is not None
        # Important: empty filename keeps flask from trying to autodetect filename,
        # as this would not work for us, because our file's are not necessarily fs files.
        return send_file(file=file_to_send,
                         mimetype=content_type,
                         as_attachment=False, attachment_filename=filename,
                         cache_timeout=10, # wiki data can change rapidly
                         add_etags=True, etag=hash, conditional=True)


class RenderableBinary(Binary):
    """ This is a base class for some binary stuff that renders with a object tag. """
    supported_mimetypes = []


class Application(Binary):
    supported_mimetypes = []


class TarMixin(object):
    """
    TarMixin offers additional functionality for tar-like items to list and
    access member files and to create new revisions by multiple posts.
    """
    def list_members(self):
        """
        list tar file contents (member file names)
        """
        self.rev.seek(0)
        tf = tarfile.open(fileobj=self.rev, mode='r')
        return tf.getnames()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        :param name: name of the data in the container file
        """
        self.rev.seek(0)
        tf = tarfile.open(fileobj=self.rev, mode='r')
        return tf.extractfile(name)

    def put_member(self, name, content, content_length, expected_members):
        """
        puts a new member file into a temporary tar container.
        If all expected members have been put, it saves the tar container
        to a new item revision.

        :param name: name of the data in the container file
        :param content: the data to store into the tar file (str or file-like)
        :param content_length: byte-length of content (for str, None can be given)
        :param expected_members: set of expected member file names
        """
        if not name in expected_members:
            raise StorageError("tried to add unexpected member %r to container item %r" % (name, self.name))
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        temp_fname = os.path.join(tempfile.gettempdir(), 'TarContainer_' +
                                  wikiutil.cache_key(usage='TarContainer', name=self.name))
        tf = tarfile.TarFile(temp_fname, mode='a')
        ti = tarfile.TarInfo(name)
        if isinstance(content, str):
            if content_length is None:
                content_length = len(content)
            content = StringIO(content) # we need a file obj
        elif not hasattr(content, 'read'):
            logging.error("unsupported content object: %r" % content)
            raise StorageError("unsupported content object: %r" % content)
        assert content_length >= 0  # we don't want -1 interpreted as 4G-1
        ti.size = content_length
        tf.addfile(ti, content)
        tf_members = set(tf.getnames())
        tf.close()
        if tf_members - expected_members:
            msg = "found unexpected members in container item %r" % self.name
            logging.error(msg)
            os.remove(temp_fname)
            raise StorageError(msg)
        if tf_members == expected_members:
            # everything we expected has been added to the tar file, save the container as revision
            meta = {"mimetype": self.mimetype}
            data = open(temp_fname, 'rb')
            self._save(meta, data, name=self.name, action=u'SAVE', mimetype=self.mimetype, comment='')
            data.close()
            os.remove(temp_fname)


class ApplicationXTar(TarMixin, Application):
    supported_mimetypes = ['application/x-tar', 'application/x-gtar']

    def feed_input_conv(self):
        return self.rev


class ZipMixin(object):
    """
    ZipMixin offers additional functionality for zip-like items to list and
    access member files.
    """
    def list_members(self):
        """
        list zip file contents (member file names)
        """
        self.rev.seek(0)
        zf = zipfile.ZipFile(self.rev, mode='r')
        return zf.namelist()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        :param name: name of the data in the zip file
        """
        self.rev.seek(0)
        zf = zipfile.ZipFile(self.rev, mode='r')
        return zf.open(name, mode='r')

    def put_member(self, name, content, content_length, expected_members):
        raise NotImplementedError


class ApplicationZip(ZipMixin, Application):
    supported_mimetypes = ['application/zip']

    def feed_input_conv(self):
        return self.rev


class PDF(Application):
    supported_mimetypes = ['application/pdf', ]


class Video(Binary):
    supported_mimetypes = ['video/', ]


class Audio(Binary):
    supported_mimetypes = ['audio/', ]


class Image(Binary):
    """ Any Image mimetype """
    supported_mimetypes = ['image/', ]


class RenderableImage(RenderableBinary):
    """ Any Image mimetype """
    supported_mimetypes = []


class SvgImage(RenderableImage):
    """ SVG images use <object> tag mechanism from RenderableBinary base class """
    supported_mimetypes = ['image/svg+xml']


class RenderableBitmapImage(RenderableImage):
    """ PNG/JPEG/GIF images use <img> tag (better browser support than <object>) """
    supported_mimetypes = [] # if mimetype is also transformable, please list
                             # in TransformableImage ONLY!


class TransformableBitmapImage(RenderableBitmapImage):
    """ We can transform (resize, rotate, mirror) some image types """
    supported_mimetypes = ['image/png', 'image/jpeg', 'image/gif', ]

    def _transform(self, content_type, size=None, transpose_op=None):
        """ resize to new size (optional), transpose according to exif infos,
            result data should be content_type.
        """
        try:
            from PIL import Image as PILImage
        except ImportError:
            # no PIL, we can't do anything, we just output the revision data as is
            return content_type, self.rev.read()

        if content_type == 'image/jpeg':
            output_type = 'JPEG'
        elif content_type == 'image/png':
            output_type = 'PNG'
        elif content_type == 'image/gif':
            output_type = 'GIF'
        else:
            raise ValueError("content_type %r not supported" % content_type)

        # revision obj has read() seek() tell(), thus this works:
        image = PILImage.open(self.rev)
        image.load()

        try:
            # if we have EXIF data, we can transpose (e.g. rotate left),
            # so the rendered image is correctly oriented:
            transpose_op = transpose_op or 1 # or self.exif['Orientation']
        except KeyError:
            transpose_op = 1 # no change

        if size is not None:
            image = image.copy() # create copy first as thumbnail works in-place
            image.thumbnail(size, PILImage.ANTIALIAS)

        transpose_func = {
            1: lambda image: image,
            2: lambda image: image.transpose(PILImage.FLIP_LEFT_RIGHT),
            3: lambda image: image.transpose(PILImage.ROTATE_180),
            4: lambda image: image.transpose(PILImage.FLIP_TOP_BOTTOM),
            5: lambda image: image.transpose(PILImage.ROTATE_90).transpose(PILImage.FLIP_TOP_BOTTOM),
            6: lambda image: image.transpose(PILImage.ROTATE_270),
            7: lambda image: image.transpose(PILImage.ROTATE_90).transpose(PILImage.FLIP_LEFT_RIGHT),
            8: lambda image: image.transpose(PILImage.ROTATE_90),
        }
        image = transpose_func[transpose_op](image)

        outfile = StringIO()
        image.save(outfile, output_type)
        data = outfile.getvalue()
        outfile.close()
        return content_type, data

    def _do_get_modified(self, hash):
        try:
            width = int(request.values.get('w'))
        except (TypeError, ValueError):
            width = None
        try:
            height = int(request.values.get('h'))
        except (TypeError, ValueError):
            height = None
        try:
            transpose = int(request.values.get('t'))
            assert 1 <= transpose <= 8
        except (TypeError, ValueError, AssertionError):
            transpose = 1
        if width or height or transpose != 1:
            # resize requested, XXX check ACL behaviour! XXX
            hash_name = HASH_ALGORITHM
            hash_hexdigest = self.rev[hash_name]
            cid = wikiutil.cache_key(usage="ImageTransform",
                                     hash_name=hash_name,
                                     hash_hexdigest=hash_hexdigest,
                                     width=width, height=height, transpose=transpose)
            c = app.cache.get(cid)
            if c is None:
                content_type = self.rev[MIMETYPE]
                size = (width or 99999, height or 99999)
                content_type, data = self._transform(content_type, size=size, transpose_op=transpose)
                headers = wikiutil.file_headers(content_type=content_type, content_length=len(data))
                app.cache.set(cid, (headers, data))
            else:
                # XXX TODO check ACL behaviour
                headers, data = c
            return Response(data, headers=headers)
        else:
            return self._do_get(hash)

    def _render_data_diff(self, oldrev, newrev):
        if PIL is None:
            # no PIL, we can't do anything, we just call the base class method
            return super(TransformableBitmapImage, self)._render_data_diff(oldrev, newrev)
        url = url_for('frontend.diffraw', item_name=self.name, rev1=oldrev.revno, rev2=newrev.revno)
        return Markup('<img src="%s" />' % escape(url))

    def _render_data_diff_raw(self, oldrev, newrev):
        hash_name = HASH_ALGORITHM
        cid = wikiutil.cache_key(usage="ImageDiff",
                                 hash_name=hash_name,
                                 hash_old=oldrev[hash_name],
                                 hash_new=newrev[hash_name])
        c = app.cache.get(cid)
        if c is None:
            if PIL is None:
                abort(404)

            content_type = newrev[MIMETYPE]
            if content_type == 'image/jpeg':
                output_type = 'JPEG'
            elif content_type == 'image/png':
                output_type = 'PNG'
            elif content_type == 'image/gif':
                output_type = 'GIF'
            else:
                raise ValueError("content_type %r not supported" % content_type)

            oldimage = PILImage.open(oldrev)
            newimage = PILImage.open(newrev)
            oldimage.load()
            newimage.load()
            diffimage = PILdiff(newimage, oldimage)
            outfile = StringIO()
            diffimage.save(outfile, output_type)
            data = outfile.getvalue()
            outfile.close()
            headers = wikiutil.file_headers(content_type=content_type, content_length=len(data))
            app.cache.set(cid, (headers, data))
        else:
            # XXX TODO check ACL behaviour
            headers, data = c
        return Response(data, headers=headers)

    def _render_data_diff_text(self, oldrev, newrev):
        return super(TransformableBitmapImage, self)._render_data_diff_text(oldrev, newrev)


class Text(Binary):
    """ Any kind of text """
    supported_mimetypes = ['text/']

    template = "modify_text.html"

    # text/plain mandates crlf - but in memory, we want lf only
    def data_internal_to_form(self, text):
        """ convert data from memory format to form format """
        return text.replace(u'\n', u'\r\n')

    def data_form_to_internal(self, data):
        """ convert data from form format to memory format """
        return data.replace(u'\r\n', u'\n')

    def data_internal_to_storage(self, text):
        """ convert data from memory format to storage format """
        return text.replace(u'\n', u'\r\n').encode(config.charset)

    def data_storage_to_internal(self, data):
        """ convert data from storage format to memory format """
        return data.decode(config.charset).replace(u'\r\n', u'\n')

    def feed_input_conv(self):
        return self.data_storage_to_internal(self.data).split(u'\n')

    def _render_data_diff(self, oldrev, newrev):
        from MoinMoin.util.diff_html import diff
        old_text = self.data_storage_to_internal(oldrev.read())
        new_text = self.data_storage_to_internal(newrev.read())
        storage_item = flaskg.storage.get_item(self.name)
        revs = storage_item.list_revisions()
        diffs = [(d[0], Markup(d[1]), d[2], Markup(d[3])) for d in diff(old_text, new_text)]
        return Markup(render_template('diff_text.html',
                                      item_name=self.name,
                                      oldrev=oldrev,
                                      newrev=newrev,
                                      min_revno=revs[0],
                                      max_revno=revs[-1],
                                      diffs=diffs,
                                     ))

    def _render_data_diff_text(self, oldrev, newrev):
        from MoinMoin.util import diff_text
        oldlines = self.data_storage_to_internal(oldrev.read()).split('\n')
        newlines = self.data_storage_to_internal(newrev.read()).split('\n')
        difflines = diff_text.diff(oldlines, newlines)
        return '\n'.join(difflines)

    def do_modify(self, template_name):
        form = TextChaizedForm.from_defaults()
        TextCha(form).amend_form()
        if template_name is None and isinstance(self.rev, DummyRev):
            return self._do_modify_show_templates()
        if template_name:
            item = Item.create(template_name)
            data_text = self.data_storage_to_internal(item.data)
        else:
            data_text = self.data_storage_to_internal(self.data)
        meta_text = self.meta_dict_to_text(self.meta)
        return render_template(self.template,
                               item_name=self.name,
                               rows_data=ROWS_DATA, rows_meta=ROWS_META, cols=COLS,
                               revno=0,
                               data_text=data_text,
                               meta_text=meta_text,
                               lang='en', direction='ltr',
                               help=self.modify_help,
                               form=form,
                               gen=make_generator(),
                              )


class MarkupItem(Text):
    """
    some kind of item with markup
    (internal links and transcluded items)
    """
    def before_revision_commit(self, newrev, data):
        """
        add ITEMLINKS and ITEMTRANSCLUSIONS metadata
        """
        super(MarkupItem, self).before_revision_commit(newrev, data)

        if hasattr(data, "read"):
            data.seek(0)
            data = data.read()
        elif isinstance(data, str):
            pass
        else:
            raise StorageError("unsupported content object: %r" % data)

        from MoinMoin.converter import default_registry as reg
        from MoinMoin.util.iri import Iri
        from MoinMoin.util.mime import Type, type_moin_document
        from MoinMoin.util.tree import moin_page

        input_conv = reg.get(Type(self.mimetype), type_moin_document)
        item_conv = reg.get(type_moin_document, type_moin_document,
                items='refs', url_root=Iri(request.url_root))

        i = Iri(scheme='wiki', authority='', path='/' + self.name)

        doc = input_conv(self.data_storage_to_internal(data).split(u'\n'))
        doc.set(moin_page.page_href, unicode(i))
        doc = item_conv(doc)

        newrev[ITEMLINKS] = item_conv.get_links()
        newrev[ITEMTRANSCLUSIONS] = item_conv.get_transclusions()

class MoinWiki(MarkupItem):
    """ MoinMoin wiki markup """
    supported_mimetypes = ['text/x.moin.wiki']


class CreoleWiki(MarkupItem):
    """ Creole wiki markup """
    supported_mimetypes = ['text/x.moin.creole']


class MediaWiki(MarkupItem):
    """ MediaWiki markup """
    supported_mimetypes = ['text/x-mediawiki']


class ReST(MarkupItem):
    """ ReStructured Text markup """
    supported_mimetypes = ['text/x-rst']


class HTML(Text):
    """
    HTML markup

    Note: As we use html_in converter to convert this to DOM and later some
          output converterter to produce output format (e.g. html_out for html
          output), all(?) unsafe stuff will get lost.

    Note: If raw revision data is accessed, unsafe stuff might be present!
    """
    supported_mimetypes = ['text/html']

    template = "modify_text_html.html"

    def do_modify(self, template_name):
        form = TextChaizedForm.from_defaults()
        TextCha(form).amend_form()
        if template_name is None and isinstance(self.rev, DummyRev):
            return self._do_modify_show_templates()
        if template_name:
            item = Item.create(template_name)
            data_text = self.data_storage_to_internal(item.data)
        else:
            data_text = self.data_storage_to_internal(self.data)
        meta_text = self.meta_dict_to_text(self.meta)
        return render_template(self.template,
                               item_name=self.name,
                               rows_data=ROWS_DATA, rows_meta=ROWS_META, cols=COLS,
                               revno=0,
                               data_text=data_text,
                               meta_text=meta_text,
                               lang='en', direction='ltr',
                               help=self.modify_help,
                               form=form,
                               gen=make_generator(),
                              )


class DocBook(MarkupItem):
    """ DocBook Document """
    supported_mimetypes = ['application/docbook+xml']

    def _convert(self, doc):
        from emeraldtree import ElementTree as ET
        from MoinMoin.converter import default_registry as reg
        from MoinMoin.util.mime import Type, type_moin_document
        from MoinMoin.util.tree import docbook, xlink

        doc = self._expand_document(doc)

        # We convert the internal representation of the document
        # into a DocBook document
        conv = reg.get(type_moin_document, Type('application/docbook+xml'))

        doc = conv(doc)

        # We determine the different namespaces of the output form
        output_namespaces = {
             docbook.namespace: '',
             xlink.namespace: 'xlink',
         }

        # We convert the result into a StringIO object
        # With the appropriate namespace
        # TODO: Some other operation should probably be done here too
        # like adding a doctype
        file_to_send = StringIO()
        tree = ET.ElementTree(doc)
        tree.write(file_to_send, namespaces=output_namespaces)

        # We determine the different parameters for the reply
        mt = MimeType(mimestr='application/docbook+xml')
        content_disposition = mt.content_disposition(app.cfg)
        content_type = mt.content_type()
        # After creation of the StringIO, we are at the end of the file
        # so position is the size the file.
        # and then we should move it back at the beginning of the file
        content_length = file_to_send.tell()
        file_to_send.seek(0)
        # Important: empty filename keeps flask from trying to autodetect filename,
        # as this would not work for us, because our file's are not necessarily fs files.
        return send_file(file=file_to_send,
                         mimetype=content_type,
                         as_attachment=False, attachment_filename=None,
                         cache_timeout=10, # wiki data can change rapidly
                         add_etags=False, etag=None, conditional=True)


class TWikiDraw(TarMixin, Image):
    """
    drawings by TWikiDraw applet. It creates three files which are stored as tar file.
    """
    supported_mimetypes = ["application/x-twikidraw"]
    modify_help = ""
    template = "modify_twikidraw.html"

    def modify(self):
        # called from modify UI/POST
        file_upload = request.files.get('filepath')
        filename = request.form['filename']
        basepath, basename = os.path.split(filename)
        basename, ext = os.path.splitext(basename)

        filecontent = file_upload.stream
        content_length = None
        if ext == '.draw': # TWikiDraw POSTs this first
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.replace("\r", "")
        elif ext == '.map':
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.strip()
        elif ext == '.png':
            #content_length = file_upload.content_length
            # XXX gives -1 for wsgiref, gives 0 for werkzeug :(
            # If this is fixed, we could use the file obj, without reading it into memory completely:
            filecontent = filecontent.read()

        self.put_member('drawing' + ext, filecontent, content_length,
                        expected_members=set(['drawing.draw', 'drawing.map', 'drawing.png']))

    def do_modify(self, template_name):
        """
        Fills params into the template for initialzing of the the java applet.
        The applet is called for doing modifications.
        """
        form = TextChaizedForm.from_defaults()
        TextCha(form).amend_form()
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=ROWS_META, cols=COLS,
                               revno=0,
                               meta_text=self.meta_dict_to_text(self.meta),
                               help=self.modify_help,
                               form=form,
                               gen=make_generator(),
                              )

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.draw')
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png')
        title = _('Edit drawing %(filename)s (opens in new window)', filename=item_name)

        mapfile = self.get_member('drawing.map')
        try:
            image_map = mapfile.read()
            mapfile.close()
        except (IOError, OSError):
            image_map = ''
        if image_map:
            # we have a image map. inline it and add a map ref to the img tag
            mapid = 'ImageMapOf' + item_name
            image_map = image_map.replace('%MAPNAME%', mapid)
            # add alt and title tags to areas
            image_map = re.sub(r'href\s*=\s*"((?!%TWIKIDRAW%).+?)"', r'href="\1" alt="\1" title="\1"', image_map)
            image_map = image_map.replace('%TWIKIDRAW%"', '%s" alt="%s" title="%s"' % (drawing_url, title, title))
            title = _('Clickable drawing: %(filename)s', filename=item_name)

            return Markup(image_map + '<img src="%s" alt="%s" usemap="#%s" />' % (png_url, title, mapid))
        else:
            return Markup('<img src="%s" alt="%s" />' % (png_url, title))

class AnyWikiDraw(TarMixin, Image):
    """
    drawings by AnyWikiDraw applet. It creates three files which are stored as tar file.
    """
    supported_mimetypes = ["application/x-anywikidraw"]
    modify_help = ""
    template = "modify_anywikidraw.html"

    def modify(self):
        # called from modify UI/POST
        file_upload = request.files.get('filepath')
        filename = request.form['filename']
        basepath, basename = os.path.split(filename)
        basename, ext = os.path.splitext(basename)
        filecontent = file_upload.stream
        content_length = None
        if ext == '.svg':
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.replace("\r", "")
        elif ext == '.map':
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.strip()
        elif ext == '.png':
            #content_length = file_upload.content_length
            # XXX gives -1 for wsgiref, gives 0 for werkzeug :(
            # If this is fixed, we could use the file obj, without reading it into memory completely:
            filecontent = filecontent.read()
        self.put_member('drawing' + ext, filecontent, content_length,
                        expected_members=set(['drawing.svg', 'drawing.map', 'drawing.png']))

    def do_modify(self, template_name):
        """
        Fills params into the template for initialzing of the the java applet.
        The applet is called for doing modifications.
        """
        form = TextChaizedForm.from_defaults()
        TextCha(form).amend_form()
        drawing_exists = 'drawing.svg' in self.list_members()
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=ROWS_META, cols=COLS,
                               revno=0,
                               meta_text=self.meta_dict_to_text(self.meta),
                               help=self.modify_help,
                               drawing_exists=drawing_exists,
                               form=form,
                               gen=make_generator(),
                              )

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.svg')
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png')
        title = _('Edit drawing %(filename)s (opens in new window)', filename=self.name)

        mapfile = self.get_member('drawing.map')
        try:
            image_map = mapfile.read()
            mapfile.close()
        except (IOError, OSError):
            image_map = ''
        if image_map:
            # ToDo mapid must become uniq
            # we have a image map. inline it and add a map ref to the img tag
            # we have also to set a unique ID
            mapid = 'ImageMapOf' + self.name
            image_map = image_map.replace(u'id="drawing.svg"', '')
            image_map = image_map.replace(u'name="drawing.svg"', u'name="%s"' % mapid)
            # unxml, because 4.01 concrete will not validate />
            image_map = image_map.replace(u'/>', u'>')
            title = _('Clickable drawing: %(filename)s', filename=self.name)
            return Markup(image_map + '<img src="%s" alt="%s" usemap="#%s" />' % (png_url, title, mapid))
        else:
            return Markup('<img src="%s" alt="%s" />' % (png_url, title))

class SvgDraw(TarMixin, Image):
    """ drawings by svg-edit. It creates two files (svg, png) which are stored as tar file. """

    supported_mimetypes = ['application/x-svgdraw']
    modify_help = ""
    template = "modify_svg-edit.html"

    def modify(self):
        # called from modify UI/POST
        file_upload = request.values.get('data')
        filename = request.form['filename']
        filecontent = file_upload.decode('base_64')
        basepath, basename = os.path.split(filename)
        basename, ext = os.path.splitext(basename)
        content_length = None

        if ext == '.png':
            filecontent = base64.urlsafe_b64decode(filecontent.split(',')[1])
        self.put_member(filename, filecontent, content_length,
                        expected_members=set(['drawing.svg', 'drawing.png']))

    def do_modify(self, template_name):
        """
        Fills params into the template for initializing of the applet.
        """
        form = TextChaizedForm.from_defaults()
        TextCha(form).amend_form()
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=ROWS_META, cols=COLS,
                               revno=0,
                               meta_text=self.meta_dict_to_text(self.meta),
                               help=self.modify_help,
                               form=form,
                               gen=make_generator(),
                              )

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.svg')
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png')
        return Markup('<img src="%s" alt="%s" />' % (png_url, drawing_url))
