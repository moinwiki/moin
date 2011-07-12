# Copyright: 2009 MoinMoin:ThomasWaldmann
# Copyright: 2009-2011 MoinMoin:ReimarBauer
# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2008,2009 MoinMoin:BastianBlank
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
from array import array

from flatland import Form, String, Integer, Boolean, Enum
from flatland.validation import Validator, Present, IsEmail, ValueBetween, URLValidator, Converted
from MoinMoin.util.forms import FileStorage

from MoinMoin.security.textcha import TextCha, TextChaizedForm, TextChaValid
from MoinMoin.signalling import item_modified
from MoinMoin.util.mimetype import MimeType
from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import moin_page, html, xlink, docbook
from MoinMoin.util.iri import Iri
from MoinMoin.util.crypto import cache_key

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

from flask import request, url_for, flash, Response, redirect, abort, escape

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
                            CONTENTTYPE, SIZE, LANGUAGE, ITEMLINKS, ITEMTRANSCLUSIONS, \
                            TAGS, ACTION, ADDRESS, HOSTNAME, USERID, EXTRA, COMMENT, \
                            HASH_ALGORITHM

COLS = 80
ROWS_DATA = 20
ROWS_META = 10


from ..util.registry import RegistryBase


class RegistryItem(RegistryBase):
    class Entry(object):
        def __init__(self, factory, content_type, priority):
            self.factory = factory
            self.content_type = content_type
            self.priority = priority

        def __call__(self, name, content_type, kw):
            if self.content_type.issupertype(content_type):
                return self.factory(name, content_type, **kw)

        def __eq__(self, other):
            if isinstance(other, self.__class__):
                return (self.factory == other.factory and
                        self.content_type == other.content_type and
                        self.priority == other.priority)
            return NotImplemented

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                if self.priority < other.priority:
                    return True
                if self.content_type != other.content_type:
                    return other.content_type.issupertype(self.content_type)
                return False
            return NotImplemented

        def __repr__(self):
            return '<%s: %s, prio %d [%r]>' % (self.__class__.__name__,
                    self.content_type,
                    self.priority,
                    self.factory)

    def get(self, name, content_type, **kw):
        for entry in self._entries:
            item = entry(name, content_type, kw)
            if item is not None:
                return item

    def register(self, factory, content_type, priority=RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        :param factory: Factory to register. Callable, must return an object.
        """
        return self._register(self.Entry(factory, content_type, priority))


item_registry = RegistryItem()


def conv_serialize(doc, namespaces):
    out = array('u')
    flaskg.clock.start('conv_serialize')
    doc.write(out.fromunicode, namespaces=namespaces, method='xml')
    out = out.tounicode()
    flaskg.clock.stop('conv_serialize')
    return out


class DummyRev(dict):
    """ if we have no stored Revision, we use this dummy """
    def __init__(self, item, contenttype):
        self[CONTENTTYPE] = contenttype
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
    def _factory(cls, name=u'', contenttype=None, **kw):
        return cls(name, contenttype=unicode(contenttype), **kw)

    @classmethod
    def create(cls, name=u'', contenttype=None, rev_no=None, item=None):
        if rev_no is None:
            rev_no = -1
        if contenttype is None:
            contenttype = 'application/x-nonexistent'

        try:
            if item is None:
                item = flaskg.storage.get_item(name)
            else:
                name = item.name
        except NoSuchItemError:
            logging.debug("No such item: %r" % name)
            item = DummyItem(name)
            rev = DummyRev(item, contenttype)
            logging.debug("Item %r, created dummy revision with contenttype %r" % (name, contenttype))
        else:
            logging.debug("Got item: %r" % name)
            try:
                rev = item.get_revision(rev_no)
                contenttype = 'application/octet-stream' # it exists
            except NoSuchRevisionError:
                try:
                    rev = item.get_revision(-1) # fall back to current revision
                    # XXX add some message about invalid revision
                except NoSuchRevisionError:
                    logging.debug("Item %r has no revisions." % name)
                    rev = DummyRev(item, contenttype)
                    logging.debug("Item %r, created dummy revision with contenttype %r" % (name, contenttype))
            logging.debug("Got item %r, revision: %r" % (name, rev_no))
        contenttype = rev.get(CONTENTTYPE) or contenttype # use contenttype in case our metadata does not provide CONTENTTYPE
        logging.debug("Item %r, got contenttype %r from revision meta" % (name, contenttype))
        logging.debug("Item %r, rev meta dict: %r" % (name, dict(rev)))

        item = item_registry.get(name, Type(contenttype), rev=rev)
        logging.debug("ItemClass %r handles %r" % (item.__class__, contenttype))
        return item

    def __init__(self, name, rev=None, contenttype=None):
        self.name = name
        self.rev = rev
        self.contenttype = contenttype

    def get_meta(self):
        return self.rev or {}
    meta = property(fget=get_meta)

    def _render_meta(self):
        # override this in child classes
        return ''

    def feed_input_conv(self):
        return self.rev

    def internal_representation(self, converters=['smiley']):
        """
        Return the internal representation of a document using a DOM Tree
        """
        flaskg.clock.start('conv_in_dom')
        hash_name = HASH_ALGORITHM
        hash_hexdigest = self.rev.get(hash_name)
        if hash_hexdigest:
            cid = cache_key(usage="internal_representation",
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
            input_conv = reg.get(Type(self.contenttype), type_moin_document)
            if not input_conv:
                raise TypeError("We cannot handle the conversion from %s to the DOM tree" % self.contenttype)
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
        include_conv = reg.get(type_moin_document, type_moin_document, includes='expandall')
        macro_conv = reg.get(type_moin_document, type_moin_document, macros='expandall')
        # TODO: Real output format
        html_conv = reg.get(type_moin_document, Type('application/x-xhtml-moin-page'))
        doc = self.internal_representation()
        doc = self._expand_document(doc)
        flaskg.clock.start('conv_dom_html')
        doc = html_conv(doc)
        flaskg.clock.stop('conv_dom_html')
        return conv_serialize(doc, {html.namespace: ''})

    def _render_data_xml(self):
        doc = self.internal_representation()
        return conv_serialize(doc,
                              {moin_page.namespace: '',
                               xlink.namespace: 'xlink',
                               html.namespace: 'html',
                              })

    def _render_data_highlight(self):
        # override this in child classes
        return ''

    def _do_modify_show_templates(self):
        # call this if the item is still empty
        rev_nos = []
        item_templates = self.get_templates(self.contenttype)
        return render_template('modify_show_template_selection.html',
                               item_name=self.name,
                               rev=self.rev,
                               contenttype=self.contenttype,
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
        written = 0
        if hasattr(content, "read"):
            while True:
                buf = content.read(bufsize)
                if not buf:
                    break
                new_rev.write(buf)
                written += len(buf)
        elif isinstance(content, str):
            new_rev.write(content)
            written += len(content)
        else:
            raise StorageError("unsupported content object: %r" % content)
        return written

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
        meta = data = contenttype_guessed = None
        contenttype_qs = request.values.get('contenttype')
        data_file = request.files.get('data_file')
        if data_file and data_file.filename: # XXX is this the right way to check if there was a file uploaded?
            data = data_file.stream
            # this is likely a guess by the browser, based on the filename
            contenttype_guessed = data_file.content_type # comes from form multipart data
        if data is None:
            # no file upload, try taking stuff from textarea
            data = request.form.get('data_text')
            if data is not None:
                # there was a data_text field with (possibly empty) content
                assert isinstance(data, unicode) # we get unicode from the form
                data = self.data_form_to_internal(data)
                data = self.data_internal_to_storage(data)
                # we know it is text and utf-8 - XXX is there a way to get the charset of the form?
                contenttype_guessed = 'text/plain;charset=utf-8'
        # data might be None here, if we have a form with just the data_file field, no file was uploaded
        # and no data_text field. this can happen if just metadata of a non-text item is edited.

        meta_text = request.form.get('meta_text')
        if meta_text is not None:
            # there was a meta_text field with (possibly empty) content
            # Note: if you get crashes here, please see the ValidJSON validator
            # to catch invalid json issues early.
            meta = self.meta_text_to_dict(meta_text)
        if meta is None:
            # no form metadata - reuse some stuff from previous metadata?
            meta = {}

        if contenttype_qs:
            # we use querystring param to FORCE content type
            meta[CONTENTTYPE] = contenttype_qs

        comment = request.form.get('comment')
        return self._save(meta, data, contenttype_guessed=contenttype_guessed, comment=comment)

    def _save(self, meta, data=None, name=None, action=u'SAVE', contenttype_guessed=None, comment=u''):
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
            contenttype_current = currentrev.get(CONTENTTYPE)
        except NoSuchRevisionError:
            currentrev = None
            rev_no = -1
            contenttype_current = None
        new_rev_no = rev_no + 1
        newrev = storage_item.create_revision(new_rev_no)
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

        if data is None:
            if currentrev is not None:
                # we don't have (new) data, just copy the old one.
                # a valid usecase of this is to just edit metadata.
                data = currentrev
            else:
                data = ''
        size = self._write_stream(data, newrev)

        # XXX if meta is from old revision, and user did not give a non-empty
        # XXX comment, re-using the old rev's comment is wrong behaviour:
        comment = unicode(comment or meta.get(COMMENT, ''))
        if comment:
            newrev[COMMENT] = comment

        if CONTENTTYPE not in newrev:
            # make sure we have CONTENTTYPE
            newrev[CONTENTTYPE] = unicode(contenttype_current or contenttype_guessed or 'application/octet-stream')

        newrev[ACTION] = unicode(action)
        self.before_revision_commit(newrev, data)
        storage_item.commit()
        item_modified.send(app._get_current_object(), item_name=name)
        return new_rev_no, size

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
        items = [(item.name, item.name[prefix_len:], item.meta.get(CONTENTTYPE))
                 for item in item_iterator]
        return sorted(items)

    def flat_index(self):
        index = self.get_index()
        index = [(fullname, relname, contenttype)
                 for fullname, relname, contenttype in index
                 if u'/' not in relname]
        return index

    index_template = 'index.html'


class NonExistent(Item):
    contenttype_groups = [
        ('markup text items', [
            ('text/x.moin.wiki;charset=utf-8', 'Wiki (MoinMoin)'),
            ('text/x.moin.creole;charset=utf-8', 'Wiki (Creole)'),
            ('text/x-mediawiki;charset=utf-8', 'Wiki (MediaWiki)'),
            ('text/x-rst;charset=utf-8', 'ReST'),
            ('application/docbook+xml;charset=utf-8', 'DocBook'),
            ('text/html;charset=utf-8', 'HTML'),
        ]),
        ('other text items', [
            ('text/plain;charset=utf-8', 'plain text'),
            ('text/x-diff;charset=utf-8', 'diff/patch'),
            ('text/x-python;charset=utf-8', 'python code'),
            ('text/csv;charset=utf-8', 'csv'),
            ('text/x-irclog;charset=utf-8', 'IRC log'),
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

    def do_get(self, force_attachment=False):
        abort(404)

    def _convert(self):
        abort(404)

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        return render_template('modify_show_type_selection.html',
                               item_name=self.name,
                               contenttype_groups=self.contenttype_groups,
                              )

item_registry.register(NonExistent._factory, Type('application/x-nonexistent'))

class ValidJSON(Validator):
    """Validator for JSON
    """
    invalid_json_msg = L_('Invalid JSON.')

    def validate(self, element, state):
        try:
            json.loads(element.value)
        except:
            return self.note_error(element, state, 'invalid_json_msg')
        return True


class Binary(Item):
    """ An arbitrary binary item, fallback class for every item mimetype. """
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

    def get_templates(self, contenttype=None):
        """ create a list of templates (for some specific contenttype) """
        from MoinMoin.storage.terms import AND, LastRevisionMetaDataMatch
        term = LastRevisionMetaDataMatch(TAGS, ['template']) # XXX there might be other tags
        if contenttype:
            term = AND(term, LastRevisionMetaDataMatch(CONTENTTYPE, contenttype))
        item_iterator = self.search_items(term)
        items = [item.name for item in item_iterator]
        return sorted(items)

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        from MoinMoin.apps.frontend.views import CommentForm
        class ModifyForm(CommentForm):
            rev = Integer.using(optional=False)
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            form['rev'] = self.rev.revno if self.rev.revno is not None else -1
        elif request.method == 'POST':
            form = ModifyForm.from_flat(request.form.items() + request.files.items())
            TextCha(form).amend_form()
            if form.validate():
                try:
                    self.modify() # XXX
                except AccessDeniedError:
                    abort(403)
                else:
                    return redirect(url_for('frontend.show_item', item_name=self.name))
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=str(ROWS_META), cols=str(COLS),
                               help=self.modify_help,
                               form=form,
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
        return _("Impossible to convert the data to the contenttype: %(contenttype)s",
                 contenttype=request.values.get('contenttype'))

    def do_get(self, force_attachment=False):
        hash = self.rev.get(HASH_ALGORITHM)
        if is_resource_modified(request.environ, hash): # use hash as etag
            return self._do_get_modified(hash, force_attachment=force_attachment)
        else:
            return Response(status=304)

    def _do_get_modified(self, hash, force_attachment=False):
        member = request.values.get('member')
        return self._do_get(hash, member, force_attachment=force_attachment)

    def _do_get(self, hash, member=None, force_attachment=False):
        if member: # content = file contained within a archive item revision
            path, filename = os.path.split(member)
            mt = MimeType(filename=filename)
            content_length = None
            file_to_send = self.get_member(member)
        else: # content = item revision
            rev = self.rev
            filename = rev.item.name
            try:
                mimestr = rev[CONTENTTYPE]
            except KeyError:
                mt = MimeType(filename=filename)
            else:
                mt = MimeType(mimestr=mimestr)
            content_length = rev[SIZE]
            file_to_send = rev
        content_type = mt.content_type()
        as_attachment = force_attachment or mt.as_attachment(app.cfg)
        return send_file(file=file_to_send,
                         mimetype=content_type,
                         as_attachment=as_attachment, attachment_filename=filename,
                         cache_timeout=10, # wiki data can change rapidly
                         add_etags=True, etag=hash, conditional=True)

item_registry.register(Binary._factory, Type('*/*'))


class RenderableBinary(Binary):
    """ Base class for some binary stuff that renders with a object tag. """


class Application(Binary):
    """ Base class for application/* """


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
                                  cache_key(usage='TarContainer', name=self.name))
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
            meta = {CONTENTTYPE: self.contenttype}
            data = open(temp_fname, 'rb')
            self._save(meta, data, name=self.name, action=u'SAVE', comment='')
            data.close()
            os.remove(temp_fname)


class ApplicationXTar(TarMixin, Application):
    """
    Tar items
    """

item_registry.register(ApplicationXTar._factory, Type('application/x-tar'))
item_registry.register(ApplicationXTar._factory, Type('application/x-gtar'))


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
    """
    Zip items
    """

item_registry.register(ApplicationZip._factory, Type('application/zip'))


class PDF(Application):
    """ PDF """

item_registry.register(PDF._factory, Type('application/pdf'))


class Video(Binary):
    """ Base class for video/* """

item_registry.register(Video._factory, Type('video/*'))


class Audio(Binary):
    """ Base class for audio/* """

item_registry.register(Audio._factory, Type('audio/*'))


class Image(Binary):
    """ Base class for image/* """

item_registry.register(Image._factory, Type('image/*'))


class RenderableImage(RenderableBinary):
    """ Base class for renderable Image mimetypes """


class SvgImage(RenderableImage):
    """ SVG images use <object> tag mechanism from RenderableBinary base class """

item_registry.register(SvgImage._factory, Type('image/svg+xml'))


class RenderableBitmapImage(RenderableImage):
    """ PNG/JPEG/GIF images use <img> tag (better browser support than <object>) """
    # if mimetype is also transformable, please register in TransformableImage ONLY!


class TransformableBitmapImage(RenderableBitmapImage):
    """ We can transform (resize, rotate, mirror) some image types """
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

    def _do_get_modified(self, hash, force_attachment=False):
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
            cid = cache_key(usage="ImageTransform",
                            hash_name=hash_name,
                            hash_hexdigest=hash_hexdigest,
                            width=width, height=height, transpose=transpose)
            c = app.cache.get(cid)
            if c is None:
                content_type = self.rev[CONTENTTYPE]
                size = (width or 99999, height or 99999)
                content_type, data = self._transform(content_type, size=size, transpose_op=transpose)
                headers = wikiutil.file_headers(content_type=content_type, content_length=len(data))
                app.cache.set(cid, (headers, data))
            else:
                # XXX TODO check ACL behaviour
                headers, data = c
            return Response(data, headers=headers)
        else:
            return self._do_get(hash, force_attachment=force_attachment)

    def _render_data_diff(self, oldrev, newrev):
        if PIL is None:
            # no PIL, we can't do anything, we just call the base class method
            return super(TransformableBitmapImage, self)._render_data_diff(oldrev, newrev)
        url = url_for('frontend.diffraw', item_name=self.name, rev1=oldrev.revno, rev2=newrev.revno)
        return Markup('<img src="%s" />' % escape(url))

    def _render_data_diff_raw(self, oldrev, newrev):
        hash_name = HASH_ALGORITHM
        cid = cache_key(usage="ImageDiff",
                        hash_name=hash_name,
                        hash_old=oldrev[hash_name],
                        hash_new=newrev[hash_name])
        c = app.cache.get(cid)
        if c is None:
            if PIL is None:
                abort(404) # TODO render user friendly error image

            content_type = newrev[CONTENTTYPE]
            if content_type == 'image/jpeg':
                output_type = 'JPEG'
            elif content_type == 'image/png':
                output_type = 'PNG'
            elif content_type == 'image/gif':
                output_type = 'GIF'
            else:
                raise ValueError("content_type %r not supported" % content_type)

            try:
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
            except (IOError, ValueError) as err:
                logging.exception("error during PILdiff: %s", err.message)
                abort(404) # TODO render user friendly error image
        else:
            # XXX TODO check ACL behaviour
            headers, data = c
        return Response(data, headers=headers)

    def _render_data_diff_text(self, oldrev, newrev):
        return super(TransformableBitmapImage, self)._render_data_diff_text(oldrev, newrev)

item_registry.register(TransformableBitmapImage._factory, Type('image/png'))
item_registry.register(TransformableBitmapImage._factory, Type('image/jpeg'))
item_registry.register(TransformableBitmapImage._factory, Type('image/gif'))


class Text(Binary):
    """ Base class for text/* """
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

    def _render_data_highlight(self):
        from MoinMoin.converter import default_registry as reg
        data_text = self.data_storage_to_internal(self.data)
        # TODO: use registry as soon as it is in there
        from MoinMoin.converter.pygments_in import Converter as PygmentsConverter
        pygments_conv = PygmentsConverter(contenttype=self.contenttype)
        doc = pygments_conv(data_text.split(u'\n'))
        # TODO: Real output format
        html_conv = reg.get(type_moin_document, Type('application/x-xhtml-moin-page'))
        doc = html_conv(doc)
        return conv_serialize(doc, {html.namespace: ''})

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        from MoinMoin.apps.frontend.views import CommentForm
        class ModifyForm(CommentForm):
            rev = Integer.using(optional=False)
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_text = String.using(optional=True).with_properties(placeholder=L_("Type your text here"))
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            if template_name is None and isinstance(self.rev, DummyRev):
                return self._do_modify_show_templates()
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            if template_name:
                item = Item.create(template_name)
                form['data_text'] = self.data_storage_to_internal(item.data)
            else:
                form['data_text'] = self.data_storage_to_internal(self.data)
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            form['rev'] = self.rev.revno if self.rev.revno is not None else -1
        elif request.method == 'POST':
            form = ModifyForm.from_flat(request.form.items() + request.files.items())
            TextCha(form).amend_form()
            if form.validate():
                try:
                    self.modify() # XXX
                except AccessDeniedError:
                    abort(403)
                else:
                    return redirect(url_for('frontend.show_item', item_name=self.name))
        return render_template(self.template,
                               item_name=self.name,
                               rows_data=str(ROWS_DATA), rows_meta=str(ROWS_META), cols=str(COLS),
                               help=self.modify_help,
                               form=form,
                              )

item_registry.register(Text._factory, Type('text/*'))


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

        input_conv = reg.get(Type(self.contenttype), type_moin_document)
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

item_registry.register(MoinWiki._factory, Type('text/x.moin.wiki'))


class CreoleWiki(MarkupItem):
    """ Creole wiki markup """

item_registry.register(CreoleWiki._factory, Type('text/x.moin.creole'))


class MediaWiki(MarkupItem):
    """ MediaWiki markup """

item_registry.register(MediaWiki._factory, Type('text/x-mediawiki'))


class ReST(MarkupItem):
    """ ReStructured Text markup """

item_registry.register(ReST._factory, Type('text/x-rst'))


class HTML(Text):
    """
    HTML markup

    Note: As we use html_in converter to convert this to DOM and later some
          output converterter to produce output format (e.g. html_out for html
          output), all(?) unsafe stuff will get lost.

    Note: If raw revision data is accessed, unsafe stuff might be present!
    """
    template = "modify_text_html.html"

item_registry.register(HTML._factory, Type('text/html'))


class DocBook(MarkupItem):
    """ DocBook Document """
    def _convert(self, doc):
        from emeraldtree import ElementTree as ET
        from MoinMoin.converter import default_registry as reg

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
        mt = MimeType(mimestr='application/docbook+xml;charset=utf-8')
        content_type = mt.content_type()
        as_attachment = mt.as_attachment(app.cfg)
        # After creation of the StringIO, we are at the end of the file
        # so position is the size the file.
        # and then we should move it back at the beginning of the file
        content_length = file_to_send.tell()
        file_to_send.seek(0)
        # Important: empty filename keeps flask from trying to autodetect filename,
        # as this would not work for us, because our file's are not necessarily fs files.
        return send_file(file=file_to_send,
                         mimetype=content_type,
                         as_attachment=as_attachment, attachment_filename=None,
                         cache_timeout=10, # wiki data can change rapidly
                         add_etags=False, etag=None, conditional=True)

item_registry.register(DocBook._factory, Type('application/docbook+xml'))


class TWikiDraw(TarMixin, Image):
    """
    drawings by TWikiDraw applet. It creates three files which are stored as tar file.
    """
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

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        from MoinMoin.apps.frontend.views import CommentForm
        class ModifyForm(CommentForm):
            rev = Integer.using(optional=False)
            # XXX as the "saving" POSTs come from TWikiDraw (not the form), editing meta_text doesn't work
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            # XXX currently this is rather pointless, as the form does not get POSTed:
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            form['rev'] = self.rev.revno if self.rev.revno is not None else -1
        elif request.method == 'POST':
            # this POST comes directly from TWikiDraw (not from Browser), thus no validation
            try:
                self.modify() # XXX
            except AccessDeniedError:
                abort(403)
            else:
                # TWikiDraw POSTs more than once, redirecting would break them
                return "OK"
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=str(ROWS_META), cols=str(COLS),
                               help=self.modify_help,
                               form=form,
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

item_registry.register(TWikiDraw._factory, Type('application/x-twikidraw'))


class AnyWikiDraw(TarMixin, Image):
    """
    drawings by AnyWikiDraw applet. It creates three files which are stored as tar file.
    """
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

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        from MoinMoin.apps.frontend.views import CommentForm
        class ModifyForm(CommentForm):
            rev = Integer.using(optional=False)
            # XXX as the "saving" POSTs come from AnyWikiDraw (not the form), editing meta_text doesn't work
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            # XXX currently this is rather pointless, as the form does not get POSTed:
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            form['rev'] = self.rev.revno if self.rev.revno is not None else -1
        elif request.method == 'POST':
            # this POST comes directly from AnyWikiDraw (not from Browser), thus no validation
            try:
                self.modify() # XXX
            except AccessDeniedError:
                abort(403)
            else:
                # AnyWikiDraw POSTs more than once, redirecting would break them
                return "OK"
        try:
            drawing_exists = 'drawing.svg' in self.list_members()
        except:
            drawing_exists = False
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=str(ROWS_META), cols=str(COLS),
                               help=self.modify_help,
                               drawing_exists=drawing_exists,
                               form=form,
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

item_registry.register(AnyWikiDraw._factory, Type('application/x-anywikidraw'))


class SvgDraw(TarMixin, Image):
    """ drawings by svg-edit. It creates two files (svg, png) which are stored as tar file. """
    modify_help = ""
    template = "modify_svg-edit.html"

    def modify(self):
        # called from modify UI/POST
        png_upload = request.values.get('png_data')
        svg_upload = request.values.get('filepath')
        filename = request.form['filename']
        png_content = png_upload.decode('base_64')
        png_content = base64.urlsafe_b64decode(png_content.split(',')[1])
        svg_content = svg_upload.decode('base_64')
        content_length = None
        self.put_member("drawing.svg", svg_content, content_length,
                        expected_members=set(['drawing.svg', 'drawing.png']))
        self.put_member("drawing.png", png_content, content_length,
                        expected_members=set(['drawing.svg', 'drawing.png']))

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        from MoinMoin.apps.frontend.views import CommentForm
        class ModifyForm(CommentForm):
            rev = Integer.using(optional=False)
            # XXX as the "saving" POSTs come from SvgDraw (not the form), editing meta_text doesn't work
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            # XXX currently this is rather pointless, as the form does not get POSTed:
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            form['rev'] = self.rev.revno if self.rev.revno is not None else -1
        elif request.method == 'POST':
            # this POST comes directly from SvgDraw (not from Browser), thus no validation
            try:
                self.modify() # XXX
            except AccessDeniedError:
                abort(403)
            else:
                # SvgDraw POSTs more than once, redirecting would break them
                return "OK"
        return render_template(self.template,
                               item_name=self.name,
                               rows_meta=str(ROWS_META), cols=str(COLS),
                               help=self.modify_help,
                               form=form,
                              )

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.svg')
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png')
        return Markup('<img src="%s" alt="%s" />' % (png_url, drawing_url))

item_registry.register(SvgDraw._factory, Type('application/x-svgdraw'))

