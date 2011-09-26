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
import itertools
from StringIO import StringIO
from array import array

from flatland import Form, String, Integer, Boolean, Enum
from flatland.validation import Validator, Present, IsEmail, ValueBetween, URLValidator, Converted

from whoosh.query import Term, And, Prefix

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
from MoinMoin.util.interwiki import url_for_item
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError, \
                                   StorageError
from MoinMoin.config import NAME, NAME_OLD, NAME_EXACT, WIKINAME, MTIME, REVERTED_TO, ACL, \
                            IS_SYSITEM, SYSITEM_VERSION,  USERGROUP, SOMEDICT, \
                            CONTENTTYPE, SIZE, LANGUAGE, ITEMLINKS, ITEMTRANSCLUSIONS, \
                            TAGS, ACTION, ADDRESS, HOSTNAME, USERID, EXTRA, COMMENT, \
                            HASH_ALGORITHM, CONTENTTYPE_GROUPS, ITEMID, REVID, DATAID, \
                            CURRENT

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
        self.item = item
        self.meta = {CONTENTTYPE: contenttype}
        self.data = StringIO('')
        self.revid = None


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
    def create(cls, name=u'', contenttype=None, rev_no=CURRENT, item=None):
        if contenttype is None:
            contenttype = u'application/x-nonexistent'

        if 1: # try:
            if item is None:
                item = flaskg.storage[name]
            else:
                name = item.name
        if not item: # except NoSuchItemError:
            logging.debug("No such item: %r" % name)
            item = DummyItem(name)
            rev = DummyRev(item, contenttype)
            logging.debug("Item %r, created dummy revision with contenttype %r" % (name, contenttype))
        else:
            logging.debug("Got item: %r" % name)
            try:
                rev = item.get_revision(rev_no)
                contenttype = u'application/octet-stream' # it exists
            except KeyError: # NoSuchRevisionError:
                try:
                    rev = item.get_revision(CURRENT) # fall back to current revision
                    # XXX add some message about invalid revision
                except KeyError: # NoSuchRevisionError:
                    logging.debug("Item %r has no revisions." % name)
                    rev = DummyRev(item, contenttype)
                    logging.debug("Item %r, created dummy revision with contenttype %r" % (name, contenttype))
            logging.debug("Got item %r, revision: %r" % (name, rev_no))
        contenttype = rev.meta.get(CONTENTTYPE) or contenttype # use contenttype in case our metadata does not provide CONTENTTYPE
        logging.debug("Item %r, got contenttype %r from revision meta" % (name, contenttype))
        #logging.debug("Item %r, rev meta dict: %r" % (name, dict(rev.meta)))

        item = item_registry.get(name, Type(contenttype), rev=rev)
        logging.debug("ItemClass %r handles %r" % (item.__class__, contenttype))
        return item

    def __init__(self, name, rev=None, contenttype=None):
        self.name = name
        self.rev = rev
        self.contenttype = contenttype

    def get_meta(self):
        return self.rev.meta
    meta = property(fget=get_meta)

    def _render_meta(self):
        # override this in child classes
        return ''

    def internal_representation(self, converters=['smiley']):
        """
        Return the internal representation of a document using a DOM Tree
        """
        flaskg.clock.start('conv_in_dom')
        hash_name = HASH_ALGORITHM
        hash_hexdigest = self.rev.meta.get(hash_name)
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
            doc = input_conv(self.rev, self.contenttype)
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
        link_conv = reg.get(type_moin_document, type_moin_document, links='extern')
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
                new_rev.data.write(buf)
                written += len(buf)
        elif isinstance(content, str):
            new_rev.data.write(content)
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
        current_rev = old_item.get_revision(CURRENT)
        # we just create a new revision with almost same meta/data to show up on RC
        self._save(current_rev, current_rev, name=name, action=u'COPY', comment=comment)

    def _rename(self, name, comment, action):
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
                contenttype_guessed = u'text/plain;charset=utf-8'
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

    def _save(self, meta, data=None, name=None, action=u'SAVE', contenttype_guessed=None, comment=u'', overwrite=False):
        if name is None:
            name = self.name
        backend = flaskg.storage
        storage_item = backend[name]
        try:
            currentrev = storage_item.get_revision(CURRENT)
            rev_no = currentrev.revid
            contenttype_current = currentrev.meta.get(CONTENTTYPE)
        except KeyError: # XXX was: NoSuchRevisionError:
            currentrev = None
            rev_no = None
            contenttype_current = None

        meta = dict(meta) # we may get a read-only dict-like, copy it

        # we store the previous (if different) and current item name into revision metadata
        # this is useful for rename history and backends that use item uids internally
        oldname = meta.get(NAME)
        if oldname and oldname != name:
            meta[NAME_OLD] = oldname
        meta[NAME] = name

        if comment:
            meta[COMMENT] = unicode(comment)

        if CONTENTTYPE not in meta:
            # make sure we have CONTENTTYPE
            meta[CONTENTTYPE] = unicode(contenttype_current or contenttype_guessed or 'application/octet-stream')

        if MTIME not in meta:
            meta[MTIME] = int(time.time())

        if ADDRESS not in meta:
            meta[ADDRESS] = u'0.0.0.0' # TODO

        if USERID not in meta and flaskg.user.valid:
            meta[USERID] = flaskg.user.itemid

        meta[ACTION] = unicode(action)

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
            data = data.encode(config.charset)

        if isinstance(data, str):
            data = StringIO(data)

        newrev = storage_item.store_revision(meta, data, overwrite=overwrite)
        item_modified.send(app._get_current_object(), item_name=name)
        return None, None # XXX was: new_revno, size

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
        revs = flaskg.storage.search(query, all_revs=False, sortedby=NAME_EXACT, limit=None)
        items = [(rev.meta[NAME], rev.meta[NAME][prefix_len:], rev.meta[CONTENTTYPE])
                 for rev in revs]
        return items

    def flat_index(self, startswith=None, selected_groups=None):
        """
        creates an top level index of sub items of this item
        if startswith is set, filtering is done on the basis of starting letter of item name
        if selected_groups is set, items whose contentype belonging to the selected contenttype_groups, are filtered.
        """
        index = self.get_index()

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
            startswith = (u'%s' % startswith, u'%s' % startswith.swapcase())
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
            subitem_name_re = u"^%s/[^/]+$" % re.escape(relname)
            regex = re.compile(subitem_name_re, re.UNICODE|re.M)
            if regex.search(all_item_text):
                hassubitem = True
            detailed_index.append((fullname, relname, contenttype, hassubitem))
        return detailed_index

    def name_initial(self, names=None):
        initials = [(name[1][0])
                   for name in names]
        return initials

class NonExistent(Item):
    def do_get(self, force_attachment=False, mimetype=None):
        abort(404)

    def _convert(self):
        abort(404)

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        return render_template('modify_show_type_selection.html',
                               item_name=self.name,
                               contenttype_groups=CONTENTTYPE_GROUPS,
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
            return self.rev.data.read()
        else:
            return ''
    data = property(fget=get_data)

    def _render_meta(self):
        return "<pre>%s</pre>" % escape(self.meta_dict_to_text(self.meta, use_filter=False))

    def get_templates(self, contenttype=None):
        """ create a list of templates (for some specific contenttype) """
        terms = [Term(WIKINAME, app.cfg.interwikiname), Term(TAGS, u'template')]
        if contenttype is not None:
            terms.append(Term(CONTENTTYPE, contenttype))
        query = And(terms)
        revs = flaskg.storage.search(query, all_revs=False, sortedby=NAME_EXACT, limit=None)
        return [rev.meta[NAME] for rev in revs]

    def do_modify(self, contenttype, template_name):
        # XXX think about and add item template support
        #if template_name is None and isinstance(self.rev, DummyRev):
        #    return self._do_modify_show_templates()
        from MoinMoin.apps.frontend.views import CommentForm
        class ModifyForm(CommentForm):
            parent = String.using(optional=True)
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            if self.rev.revid:
                form['parent'] = self.rev.revid
        elif request.method == 'POST':
            form = ModifyForm.from_flat(request.form.items() + request.files.items())
            TextCha(form).amend_form()
            if form.validate():
                try:
                    self.modify() # XXX
                except AccessDeniedError:
                    abort(403)
                else:
                    return redirect(url_for_item(self.name))
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
        if oldrev.meta[hash_name] == newrev.meta[hash_name]:
            return _("The items have the same data hash code (that means they very likely have the same data).")
        else:
            return _("The items have different data.")

    _render_data_diff_text = _render_data_diff
    _render_data_diff_raw = _render_data_diff

    def _convert(self):
        return _("Impossible to convert the data to the contenttype: %(contenttype)s",
                 contenttype=request.values.get('contenttype'))

    def do_get(self, force_attachment=False, mimetype=None):
        hash = self.rev.meta.get(HASH_ALGORITHM)
        if is_resource_modified(request.environ, hash): # use hash as etag
            return self._do_get_modified(hash, force_attachment=force_attachment, mimetype=mimetype)
        else:
            return Response(status=304)

    def _do_get_modified(self, hash, force_attachment=False, mimetype=None):
        member = request.values.get('member')
        return self._do_get(hash, member, force_attachment=force_attachment, mimetype=mimetype)

    def _do_get(self, hash, member=None, force_attachment=False, mimetype=None):
        if member: # content = file contained within a archive item revision
            path, filename = os.path.split(member)
            mt = MimeType(filename=filename)
            content_length = None
            file_to_send = self.get_member(member)
        else: # content = item revision
            rev = self.rev
            filename = rev.item.name
            try:
                mimestr = rev.meta[CONTENTTYPE]
            except KeyError:
                mt = MimeType(filename=filename)
            else:
                mt = MimeType(mimestr=mimestr)
            content_length = rev.meta[SIZE]
            file_to_send = rev.data
        if mimetype:
            content_type = mimetype
        else:
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
        self.rev.data.seek(0)
        tf = tarfile.open(fileobj=self.rev.data, mode='r')
        return tf.getnames()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        :param name: name of the data in the container file
        """
        self.rev.data.seek(0)
        tf = tarfile.open(fileobj=self.rev.data, mode='r')
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
        self.rev.data.seek(0)
        zf = zipfile.ZipFile(self.rev.data, mode='r')
        return zf.namelist()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        :param name: name of the data in the zip file
        """
        self.rev.data.seek(0)
        zf = zipfile.ZipFile(self.rev.data, mode='r')
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
            return content_type, self.rev.data.read()

        if content_type == 'image/jpeg':
            output_type = 'JPEG'
        elif content_type == 'image/png':
            output_type = 'PNG'
        elif content_type == 'image/gif':
            output_type = 'GIF'
        else:
            raise ValueError("content_type %r not supported" % content_type)

        # revision obj has read() seek() tell(), thus this works:
        image = PILImage.open(self.rev.data)
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

    def _do_get_modified(self, hash, force_attachment=False, mimetype=None):
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
            hash_hexdigest = self.rev.meta[hash_name]
            cid = cache_key(usage="ImageTransform",
                            hash_name=hash_name,
                            hash_hexdigest=hash_hexdigest,
                            width=width, height=height, transpose=transpose)
            c = app.cache.get(cid)
            if c is None:
                if mimetype:
                    content_type = mimetype
                else:
                    content_type = self.rev.meta[CONTENTTYPE]
                size = (width or 99999, height or 99999)
                content_type, data = self._transform(content_type, size=size, transpose_op=transpose)
                headers = wikiutil.file_headers(content_type=content_type, content_length=len(data))
                app.cache.set(cid, (headers, data))
            else:
                # XXX TODO check ACL behaviour
                headers, data = c
            return Response(data, headers=headers)
        else:
            return self._do_get(hash, force_attachment=force_attachment, mimetype=mimetype)

    def _render_data_diff(self, oldrev, newrev):
        if PIL is None:
            # no PIL, we can't do anything, we just call the base class method
            return super(TransformableBitmapImage, self)._render_data_diff(oldrev, newrev)
        url = url_for('frontend.diffraw', item_name=self.name, rev1=oldrev.revid, rev2=newrev.revid)
        return Markup('<img src="%s" />' % escape(url))

    def _render_data_diff_raw(self, oldrev, newrev):
        hash_name = HASH_ALGORITHM
        cid = cache_key(usage="ImageDiff",
                        hash_name=hash_name,
                        hash_old=oldrev.meta[hash_name],
                        hash_new=newrev.meta[hash_name])
        c = app.cache.get(cid)
        if c is None:
            if PIL is None:
                abort(404) # TODO render user friendly error image

            content_type = newrev.meta[CONTENTTYPE]
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

    def _render_data_diff(self, oldrev, newrev):
        from MoinMoin.util.diff_html import diff
        old_text = self.data_storage_to_internal(oldrev.data.read())
        new_text = self.data_storage_to_internal(newrev.data.read())
        storage_item = flaskg.storage[self.name]
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
        oldlines = self.data_storage_to_internal(oldrev.data.read()).split('\n')
        newlines = self.data_storage_to_internal(newrev.data.read()).split('\n')
        difflines = diff_text.diff(oldlines, newlines)
        return '\n'.join(difflines)

    def _render_data_highlight(self):
        from MoinMoin.converter import default_registry as reg
        data_text = self.data_storage_to_internal(self.data)
        # TODO: use registry as soon as it is in there
        from MoinMoin.converter.pygments_in import Converter as PygmentsConverter
        pygments_conv = PygmentsConverter(contenttype=self.contenttype)
        doc = pygments_conv(data_text)
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
            parent = String.using(optional=True)
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
            if self.rev.revid:
                form['parent'] = self.rev.revid
        elif request.method == 'POST':
            form = ModifyForm.from_flat(request.form.items() + request.files.items())
            TextCha(form).amend_form()
            if form.validate():
                try:
                    self.modify() # XXX
                except AccessDeniedError:
                    abort(403)
                else:
                    return redirect(url_for_item(self.name))
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
            parent = String.using(optional=True)
            # XXX as the "saving" POSTs come from TWikiDraw (not the form), editing meta_text doesn't work
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            # XXX currently this is rather pointless, as the form does not get POSTed:
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            if self.rev.revid:
                form['parent'] = self.rev.revid
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
            parent = String.using(optional=True)
            # XXX as the "saving" POSTs come from AnyWikiDraw (not the form), editing meta_text doesn't work
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            # XXX currently this is rather pointless, as the form does not get POSTed:
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            if self.rev.revid:
                form['parent'] = self.rev.revid
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
            parent = String.using(optional=True)
            # XXX as the "saving" POSTs come from SvgDraw (not the form), editing meta_text doesn't work
            meta_text = String.using(optional=False).with_properties(placeholder=L_("MetaData (JSON)")).validated_by(ValidJSON())
            data_file = FileStorage.using(optional=True, label=L_('Upload file:'))

        if request.method == 'GET':
            form = ModifyForm.from_defaults()
            TextCha(form).amend_form()
            # XXX currently this is rather pointless, as the form does not get POSTed:
            form['meta_text'] = self.meta_dict_to_text(self.meta)
            if self.rev.revid:
                form['parent'] = self.rev.revid
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

