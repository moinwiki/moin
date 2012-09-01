# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2009 MoinMoin:ThomasWaldmann
# Copyright: 2009-2011 MoinMoin:ReimarBauer
# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2008,2009 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - item contents

    Classes handling the content part of items (ie. minus metadata). The
    content part is sometimes called the "data" part in other places, but is
    always called content in this module to avoid confusion.

    Each class in this module corresponds to a contenttype value.
"""

import os, re, base64
import tarfile
import zipfile
import tempfile
from StringIO import StringIO
from array import array
from collections import namedtuple

from flask import current_app as app
from flask import g as flaskg
from flask import request, url_for, Response, abort, escape

from flatland import Form, String

from jinja2 import Markup

from werkzeug import is_resource_modified

from whoosh.query import Term, And

try:
    import PIL
    from PIL import Image as PILImage
    from PIL.ImageChops import difference as PILdiff
except ImportError:
    PIL = None

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil, config
from MoinMoin.i18n import _, L_
from MoinMoin.themes import render_template
from MoinMoin.storage.error import StorageError
from MoinMoin.util.send_file import send_file
from MoinMoin.util.registry import RegistryBase
from MoinMoin.util.mimetype import MimeType
from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import moin_page, html, xlink, docbook
from MoinMoin.util.iri import Iri
from MoinMoin.util.crypto import cache_key
from MoinMoin.forms import File
from MoinMoin.constants.keys import (
    NAME, NAME_EXACT, WIKINAME, CONTENTTYPE, SIZE, TAGS, HASH_ALGORITHM
    )


COLS = 80
ROWS_DATA = 20


class RegistryContent(RegistryBase):
    class Entry(namedtuple('Entry', 'factory content_type priority')):
        def __call__(self, content_type, *args, **kw):
            if self.content_type.issupertype(Type(content_type)):
                return self.factory(content_type, *args, **kw)

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                if self.priority != other.priority:
                    return self.priority < other.priority
                if self.content_type != other.content_type:
                    return other.content_type.issupertype(self.content_type)
                return False
            return NotImplemented

    def register(self, factory, content_type, priority=RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        :param factory: Factory to register. Callable, must return an object.
        """
        return self._register(self.Entry(factory, content_type, priority))


content_registry = RegistryContent()

def register(cls):
    content_registry.register(cls._factory, Type(cls.contenttype))
    return cls


def conv_serialize(doc, namespaces, method='polyglot'):
    out = array('u')
    flaskg.clock.start('conv_serialize')
    doc.write(out.fromunicode, namespaces=namespaces, method=method)
    out = out.tounicode()
    flaskg.clock.stop('conv_serialize')
    return out


class Content(object):
    """
    Base for content classes defining some helpers, agnostic about content
    data.
    """
    @classmethod
    def _factory(cls, *args, **kw):
        return cls(*args, **kw)

    @classmethod
    def create(cls, contenttype, item=None):
        content = content_registry.get(contenttype, item)
        logging.debug("Content class {0!r} handles {1!r}".format(content.__class__, contenttype))
        return content

    def __init__(self, contenttype, item=None):
        # We need to keep the exact contenttype since contents may be handled
        # by a Content subclass with wildcard contenttype (eg. an unknown
        # contenttype some/type gets handled by Binary)
        # TODO use Type instead of strings?
        self.contenttype = contenttype
        self.item = item

    # XXX For backward-compatibility (so code can be moved from Item
    # untouched), remove soon
    @property
    def rev(self):
        return self.item.rev

    @property
    def name(self):
        return self.item.name

    def get_data(self):
        return '' # TODO create a better method for binary stuff
    data = property(fget=get_data)

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
                raise TypeError("We cannot handle the conversion from {0} to the DOM tree".format(self.contenttype))
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
        # TODO: Real output format
        doc = self.internal_representation()
        doc = self._expand_document(doc)
        flaskg.clock.start('conv_dom_html')
        html_conv = reg.get(type_moin_document, Type('application/x-xhtml-moin-page'))
        doc = html_conv(doc)
        flaskg.clock.stop('conv_dom_html')
        rendered_data = conv_serialize(doc, {html.namespace: ''})
        return rendered_data

    def _render_data_xml(self):
        doc = self.internal_representation()
        return conv_serialize(doc,
                              {moin_page.namespace: '',
                               xlink.namespace: 'xlink',
                               html.namespace: 'html',
                              },
                              'xml')

    def _render_data_highlight(self):
        # override this in child classes
        return ''

    def get_templates(self, contenttype=None):
        """ create a list of templates (for some specific contenttype) """
        terms = [Term(WIKINAME, app.cfg.interwikiname), Term(TAGS, u'template')]
        if contenttype is not None:
            terms.append(Term(CONTENTTYPE, contenttype))
        query = And(terms)
        revs = flaskg.storage.search(query, sortedby=NAME_EXACT, limit=None)
        return [rev.meta[NAME] for rev in revs]


@register
class NonExistentContent(Content):
    """Dummy Content to use with NonExistent."""
    contenttype = 'application/x-nonexistent'

    def do_get(self, force_attachment=False, mimetype=None):
        abort(404)

    def _convert(self, doc):
        abort(404)


@register
class Binary(Content):
    """ An arbitrary binary item, fallback class for every item mimetype. """
    contenttype = '*/*'

    # XXX reads item rev data into memory!
    def get_data(self):
        if self.rev is not None:
            return self.rev.data.read()
        else:
            return ''
    data = property(fget=get_data)

    class ModifyForm(Form):
        template = 'modify_binary.html'
        help = """\
There is no help, you're doomed!
"""
        data_file = File.using(optional=True, label=L_('Upload file:'))

        def _load(self, item):
            pass

        def _dump(self, item):
            data_file = self['data_file'].value
            if data_file:
                data = data_file.stream
                # this is likely a guess by the browser, based on the filename
                contenttype_guessed = data_file.content_type # comes from form multipart data
                return data, contenttype_guessed
            else:
                return None, None

    def _render_data_diff(self, oldrev, newrev):
        hash_name = HASH_ALGORITHM
        if oldrev.meta[hash_name] == newrev.meta[hash_name]:
            return _("The items have the same data hash code (that means they very likely have the same data).")
        else:
            return _("The items have different data.")

    _render_data_diff_text = _render_data_diff
    _render_data_diff_raw = _render_data_diff

    def _render_data_diff_atom(self, oldrev, newrev):
        return render_template('atom.html',
                               oldrev=oldrev, newrev=newrev, get='binary',
                               content=Markup(self._render_data()))

    def _convert(self, doc):
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
            raise StorageError("tried to add unexpected member {0!r} to container item {1!r}".format(name, self.name))
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
            logging.error("unsupported content object: {0!r}".format(content))
            raise StorageError("unsupported content object: {0!r}".format(content))
        assert content_length >= 0  # we don't want -1 interpreted as 4G-1
        ti.size = content_length
        tf.addfile(ti, content)
        tf_members = set(tf.getnames())
        tf.close()
        if tf_members - expected_members:
            msg = "found unexpected members in container item {0!r}".format(self.name)
            logging.error(msg)
            os.remove(temp_fname)
            raise StorageError(msg)
        if tf_members == expected_members:
            # everything we expected has been added to the tar file, save the container as revision
            meta = {CONTENTTYPE: self.contenttype}
            data = open(temp_fname, 'rb')
            self.item._save(meta, data, name=self.name, action=u'SAVE', comment='')
            data.close()
            os.remove(temp_fname)


@register
class ApplicationXTar(TarMixin, Application):
    """
    Tar items
    """
    contenttype = 'application/x-tar'


@register
class ApplicationXGTar(ApplicationXTar):
    """
    Compressed tar items
    """
    contenttype = 'application/x-gtar'


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


@register
class ApplicationZip(ZipMixin, Application):
    """
    Zip items
    """
    contenttype = 'application/zip'


@register
class PDF(Application):
    """ PDF """
    contenttype = 'application/pdf'


@register
class Video(Binary):
    """ Base class for video/* """
    contenttype = 'video/*'


@register
class Audio(Binary):
    """ Base class for audio/* """
    contenttype = 'audio/*'


@register
class Image(Binary):
    """ Base class for image/* """
    contenttype = 'image/*'


class RenderableImage(RenderableBinary):
    """ Base class for renderable Image mimetypes """


@register
class SvgImage(RenderableImage):
    """ SVG images use <object> tag mechanism from RenderableBinary base class """
    contenttype = 'image/svg+xml'


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
            raise ValueError("content_type {0!r} not supported".format(content_type))

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

    def _render_data_diff_atom(self, oldrev, newrev):
        if PIL is None:
            # no PIL, we can't do anything, we just call the base class method
            return super(TransformableBitmapImage, self)._render_data_diff_atom(oldrev, newrev)
        url = url_for('frontend.diffraw', _external=True, item_name=self.name, rev1=oldrev.revid, rev2=newrev.revid)
        return render_template('atom.html',
                               oldrev=oldrev, newrev=newrev, get='binary',
                               content=Markup(u'<img src="{0}" />'.format(escape(url))))

    def _render_data_diff(self, oldrev, newrev):
        if PIL is None:
            # no PIL, we can't do anything, we just call the base class method
            return super(TransformableBitmapImage, self)._render_data_diff(oldrev, newrev)
        url = url_for('frontend.diffraw', item_name=self.name, rev1=oldrev.revid, rev2=newrev.revid)
        return Markup(u'<img src="{0}" />'.format(escape(url)))

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
                raise ValueError("content_type {0!r} not supported".format(content_type))

            try:
                oldimage = PILImage.open(oldrev.data)
                newimage = PILImage.open(newrev.data)
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
                logging.exception("error during PILdiff: {0}".format(err.message))
                abort(404) # TODO render user friendly error image
        else:
            # XXX TODO check ACL behaviour
            headers, data = c
        return Response(data, headers=headers)

    def _render_data_diff_text(self, oldrev, newrev):
        return super(TransformableBitmapImage, self)._render_data_diff_text(oldrev, newrev)


@register
class PNG(TransformableBitmapImage):
    """ PNG image. """
    contenttype = 'image/png'


@register
class JPEG(TransformableBitmapImage):
    """ JPEG image. """
    contenttype = 'image/jpeg'


@register
class GIF(TransformableBitmapImage):
    """ GIF image. """
    contenttype = 'image/gif'


@register
class Text(Binary):
    """ Base class for text/* """
    contenttype = 'text/*'

    class ModifyForm(Binary.ModifyForm):
        template = 'modify_text.html'
        data_text = String.using(strip=False, optional=True).with_properties(placeholder=L_("Type your text here"))
        rows = ROWS_DATA
        cols = COLS

        def _load(self, item):
            super(Text.ModifyForm, self)._load(item)
            data = item.data
            data = item.data_storage_to_internal(data)
            data = item.data_internal_to_form(data)
            self['data_text'] = data

        def _dump(self, item):
            data, contenttype_guessed = super(Text.ModifyForm, self)._dump(item)
            if data is None:
                data = self['data_text'].value
                data = item.data_form_to_internal(data)
                data = item.data_internal_to_storage(data)
                # we know it is text and utf-8 - XXX is there a way to get the charset of the form?
                contenttype_guessed = u'text/plain;charset=utf-8'
            return data, contenttype_guessed

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

    def _get_data_diff_html(self, oldrev, newrev, template):
        from MoinMoin.util.diff_html import diff
        old_text = self.data_storage_to_internal(oldrev.data.read())
        new_text = self.data_storage_to_internal(newrev.data.read())
        storage_item = flaskg.storage[self.name]
        diffs = [(d[0], Markup(d[1]), d[2], Markup(d[3])) for d in diff(old_text, new_text)]
        return render_template(template,
                               item_name=self.name,
                               oldrev=oldrev,
                               newrev=newrev,
                               diffs=diffs,
                               )

    def _render_data_diff_atom(self, oldrev, newrev):
        """ renders diff in HTML for atom feed """
        return self._get_data_diff_html(oldrev, newrev, 'diff_text_atom.html')

    def _render_data_diff(self, oldrev, newrev):
        return self._get_data_diff_html(oldrev, newrev, 'diff_text.html')

    def _render_data_diff_text(self, oldrev, newrev):
        from MoinMoin.util import diff_text
        oldlines = self.data_storage_to_internal(oldrev.data.read()).split('\n')
        newlines = self.data_storage_to_internal(newrev.data.read()).split('\n')
        difflines = diff_text.diff(oldlines, newlines)
        return '\n'.join(difflines)

    _render_data_diff_raw = _render_data_diff

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


class MarkupItem(Text):
    """
    some kind of item with markup
    (internal links and transcluded items)
    """


@register
class MoinWiki(MarkupItem):
    """ MoinMoin wiki markup """
    contenttype = 'text/x.moin.wiki'


@register
class CreoleWiki(MarkupItem):
    """ Creole wiki markup """
    contenttype = 'text/x.moin.creole'


@register
class MediaWiki(MarkupItem):
    """ MediaWiki markup """
    contenttype = 'text/x-mediawiki'


@register
class ReST(MarkupItem):
    """ ReStructured Text markup """
    contenttype = 'text/x-rst'


@register
class Markdown(MarkupItem):
    """ Markdown markup """
    contenttype = 'text/x-markdown'


@register
class HTML(Text):
    """
    HTML markup

    Note: As we use html_in converter to convert this to DOM and later some
          output converterter to produce output format (e.g. html_out for html
          output), all(?) unsafe stuff will get lost.

    Note: If raw revision data is accessed, unsafe stuff might be present!
    """
    contenttype = 'text/html'

    class ModifyForm(Text.ModifyForm):
        template = "modify_text_html.html"


@register
class DocBook(MarkupItem):
    """ DocBook Document """
    contenttype = 'application/docbook+xml'

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


class Draw(TarMixin, Image):
    """
    Base class for *Draw that use special Java/Javascript applets to modify and store data in a tar file.
    """
    class ModifyForm(Binary.ModifyForm):
        # Set the workaround flag respected in modify.html
        is_draw = True

    def handle_post():
        raise NotImplementedError


@register
class TWikiDraw(Draw):
    """
    drawings by TWikiDraw applet. It creates three files which are stored as tar file.
    """
    contenttype = 'application/x-twikidraw'

    class ModifyForm(Draw.ModifyForm):
        template = "modify_twikidraw.html"
        help = ""

    def handle_post(self):
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

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.draw', rev=self.rev.revid)
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png', rev=self.rev.revid)
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
            image_map = image_map.replace('%TWIKIDRAW%"', '{0}" alt="{1}" title="{2}"'.format((drawing_url, title, title)))
            title = _('Clickable drawing: %(filename)s', filename=item_name)

            return Markup(image_map + u'<img src="{0}" alt="{1}" usemap="#{2}" />'.format(png_url, title, mapid))
        else:
            return Markup(u'<img src="{0}" alt="{1}" />'.format(png_url, title))


@register
class AnyWikiDraw(Draw):
    """
    drawings by AnyWikiDraw applet. It creates three files which are stored as tar file.
    """
    contenttype = 'application/x-anywikidraw'

    class ModifyForm(Draw.ModifyForm):
        template = "modify_anywikidraw.html"
        help = ""
        def _load(self, item):
            super(AnyWikiDraw.ModifyForm, self)._load(item)
            try:
                drawing_exists = 'drawing.svg' in item.list_members()
            except tarfile.TarError: # item doesn't exist yet
                drawing_exists = False
            self.drawing_exists = drawing_exists

    def handle_post(self):
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

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.svg', rev=self.rev.revid)
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png', rev=self.rev.revid)
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
            image_map = image_map.replace(u'name="drawing.svg"', u'name="{0}"'.format(mapid))
            # unxml, because 4.01 concrete will not validate />
            image_map = image_map.replace(u'/>', u'>')
            title = _('Clickable drawing: %(filename)s', filename=self.name)
            return Markup(image_map + u'<img src="{0}" alt="{1}" usemap="#{2}" />'.format(png_url, title, mapid))
        else:
            return Markup(u'<img src="{0}" alt="{1}" />'.format(png_url, title))


@register
class SvgDraw(Draw):
    """ drawings by svg-edit. It creates two files (svg, png) which are stored as tar file. """
    contenttype = 'application/x-svgdraw'

    class ModifyForm(Draw.ModifyForm):
        template = "modify_svg-edit.html"
        help = ""

    def handle_post(self):
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

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        item_name = self.name
        drawing_url = url_for('frontend.get_item', item_name=item_name, member='drawing.svg', rev=self.rev.revid)
        png_url = url_for('frontend.get_item', item_name=item_name, member='drawing.png', rev=self.rev.revid)
        return Markup(u'<img src="{0}" alt="{1}" />'.format(png_url, drawing_url))
