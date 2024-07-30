# Copyright: 2009 MoinMoin:ThomasWaldmann
# Copyright: 2009-2011 MoinMoin:ReimarBauer
# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2008,2009 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2010 MoinMoin:DiogenesAugusto
# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - item contents

    Classes handling the content part of items (ie. minus metadata). The
    content part is sometimes called the "data" part in other places, but is
    always called content in this module to avoid confusion.

    Each class in this module corresponds to a contenttype value.
"""

import os
import time
import uuid
import base64
import tarfile
import zipfile
import tempfile
from io import BytesIO
from array import array
from collections import namedtuple
from operator import attrgetter

from flask import current_app as app
from flask import g as flaskg
from flask import request, url_for, Response, abort

from flatland import Form, String

from markupsafe import Markup, escape

from werkzeug.http import is_resource_modified

from whoosh.query import Term, And

try:
    import PIL
    from PIL import Image as PILImage
    from PIL.ImageChops import difference as PILdiff
except ImportError:
    PIL = PILImage = PILdiff = None

from moin import wikiutil
from moin.i18n import _, L_
from moin.themes import render_template
from moin.storage.error import StorageError
from moin.utils.send_file import send_file
from moin.utils.registry import RegistryBase
from moin.utils.mimetype import MimeType
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page, html, xlink, docbook
from moin.utils.iri import Iri
from moin.utils.diff_text import diff as text_diff
from moin.utils.diff_html import diff as html_diff
from moin.utils.crypto import cache_key
from moin.utils.clock import timed
from moin.utils.interwiki import get_download_file_name
from moin.forms import File
from moin.constants.contenttypes import (
    GROUP_MARKUP_TEXT,
    GROUP_OTHER_TEXT,
    GROUP_IMAGE,
    GROUP_AUDIO,
    GROUP_VIDEO,
    GROUP_DRAWING,
    GROUP_OTHER,
    CONTENTTYPE_NONEXISTENT,
    CHARSET,
)
from moin.constants.keys import (
    NAME_EXACT,
    WIKINAME,
    CONTENTTYPE,
    TAGS,
    TEMPLATE,
    HASH_ALGORITHM,
    ACTION_SAVE,
    NAMESPACE,
)

from moin import log

logging = log.getLogger(__name__)


COLS = 80
ROWS_DATA = 20


class RegistryContent(RegistryBase):
    class Entry(
        namedtuple("Entry", "factory content_type default_contenttype_params display_name ingroup_order priority")
    ):
        def __call__(self, content_type, *args, **kw):
            if self.content_type.issupertype(Type(content_type)):
                return self.factory(content_type, *args, **kw)

        def __lt__(self, other):
            if isinstance(other, self.__class__):
                # Within the registry, content_type is sorted in descending
                # order (more specific first) while priority is in ascending
                # order (smaller first).
                return (other.content_type, self.priority) < (self.content_type, other.priority)
            return NotImplemented

    def __init__(self, group_names):
        super().__init__()
        self.group_names = group_names
        self.groups = {g: [] for g in group_names}

    def register(self, e, group):
        """
        Register a contenttype entry and optionally add it to a specific group.
        """
        # If group is specified and contenttype is not a wildcard one
        if group and e.content_type.type and e.content_type.subtype:
            if group not in self.groups:
                raise ValueError(f"Unknown group name: {group}")
            self.groups[group].append(e)
            self.groups[group].sort(key=attrgetter("ingroup_order"))
        return self._register(e)


content_registry = RegistryContent(
    [GROUP_MARKUP_TEXT, GROUP_OTHER_TEXT, GROUP_IMAGE, GROUP_AUDIO, GROUP_VIDEO, GROUP_DRAWING, GROUP_OTHER]
)


def register(cls):
    content_registry.register(
        RegistryContent.Entry(
            cls._factory,
            Type(cls.contenttype),
            cls.default_contenttype_params,
            cls.display_name,
            cls.ingroup_order,
            RegistryContent.PRIORITY_MIDDLE,
        ),
        cls.group,
    )
    return cls


def content_registry_enable(contenttype_enabled):
    """Remove content types from the registry that are not explicitly enabled"""
    groups_enabled = {g: [] for g in content_registry.group_names}
    for group in content_registry.group_names:
        for e in content_registry.groups[group]:
            if e.display_name and e.display_name in contenttype_enabled:
                groups_enabled[group].append(e)
                logging.debug(f"Enable contenttype {e.display_name} in group {group}")
    content_registry.groups = groups_enabled


def content_registry_disable(contenttype_disabled):
    """Remove disabled content types from registry"""
    groups_enabled = {g: [] for g in content_registry.group_names}
    for group in content_registry.group_names:
        for e in content_registry.groups[group]:
            if not e.display_name or e.display_name not in contenttype_disabled:
                groups_enabled[group].append(e)
            else:
                logging.debug(f"Disable contenttype {e.display_name} in group {group}")
    content_registry.groups = groups_enabled


def conv_serialize(doc, namespaces, method="polyglot"):
    out = array("u")
    doc.write(out.fromunicode, namespaces=namespaces, method=method)
    out = out.tounicode()
    return out


class Content:
    """
    Base for content classes defining some helpers, agnostic about content
    data.
    """

    # placeholder values for registry entry properties
    contenttype = None
    default_contenttype_params = {}
    display_name = None
    group = GROUP_OTHER
    ingroup_order = 0

    @classmethod
    def _factory(cls, *args, **kw):
        return cls(*args, **kw)

    @classmethod
    def create(cls, contenttype, item=None):
        content = content_registry.get(contenttype, item)
        logging.debug(f"Content class {content.__class__!r} handles {contenttype!r}")
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
        return ""  # TODO create a better method for binary stuff

    data = property(fget=get_data)

    @timed("conv_in_dom")
    def internal_representation(self, attributes=None, preview=None):
        """
        Return the internal representation of a document using a DOM Tree
        """
        doc = cid = None
        if preview is None:
            hash_name = HASH_ALGORITHM
            hash_hexdigest = self.rev.meta.get(hash_name)
            if hash_hexdigest:
                cid = cache_key(
                    usage="internal_representation",
                    hash_name=hash_name,
                    hash_hexdigest=hash_hexdigest,
                    attrs=repr(attributes),
                )
                doc = app.cache.get(cid)
        if doc is None:
            # We will see if we can perform the conversion:
            # FROM_mimetype --> DOM
            # if so we perform the transformation, otherwise we don't
            from moin.converters import default_registry as reg

            input_conv = reg.get(Type(self.contenttype), type_moin_document)
            if not input_conv:
                raise TypeError(f"We cannot handle the conversion from {self.contenttype} to the DOM tree")
            smiley_conv = reg.get(type_moin_document, type_moin_document, icon="smiley")

            # We can process the conversion
            name = self.rev.fqname.fullname if self.rev else self.name
            links = Iri(scheme="wiki", authority="", path="/" + name)
            doc = input_conv(preview or self.rev, self.contenttype, arguments=attributes)
            # XXX is the following assuming that the top element of the doc tree
            # is a moin_page.page element? if yes, this is the wrong place to do that
            # as not every doc will have that element (e.g. for images, we just get
            # moin_page.object, for a tar item, we get a moin_page.table):
            doc.set(moin_page.page_href, str(links))
            if self.contenttype.startswith(("text/x.moin.wiki", "text/x-mediawiki", "text/x.moin.creole")):
                doc = smiley_conv(doc)
            if cid:
                app.cache.set(cid, doc)
        return doc

    def _expand_document(self, doc):
        from moin.converters import default_registry as reg

        flaskg.add_lineno_attr = False  # do not add data-lineno attr for transclusions, footnotes, etc.
        include_conv = reg.get(type_moin_document, type_moin_document, includes="expandall")
        macro_conv = reg.get(type_moin_document, type_moin_document, macros="expandall")
        nowiki_conv = reg.get(type_moin_document, type_moin_document, nowiki="expandall")
        link_conv = reg.get(type_moin_document, type_moin_document, links="extern")
        flaskg.clock.start("nowiki")
        doc = nowiki_conv(doc)
        flaskg.clock.stop("nowiki")
        flaskg.clock.start("conv_include")
        doc = include_conv(doc)
        flaskg.clock.stop("conv_include")
        flaskg.clock.start("conv_macro")
        doc = macro_conv(doc)
        flaskg.clock.stop("conv_macro")
        flaskg.clock.start("conv_link")
        doc = link_conv(doc)
        flaskg.clock.stop("conv_link")
        if "regex" in request.args:
            highlight_conv = reg.get(type_moin_document, type_moin_document, highlight="highlight")
            flaskg.clock.start("highlight")
            doc = highlight_conv(doc)
            flaskg.clock.stop("highlight")
        return doc

    def _render_data(self, preview=None):
        try:
            from moin.converters import default_registry as reg

            # TODO: Real output format
            doc = self.internal_representation(preview=preview)
            doc = self._expand_document(doc)
            flaskg.clock.start("conv_dom_html")
            html_conv = reg.get(type_moin_document, Type("application/x-xhtml-moin-page"))
            doc = html_conv(doc)
            flaskg.clock.stop("conv_dom_html")
            rendered_data = conv_serialize(doc, {html.namespace: ""})
        except Exception:
            # we really want to make sure that invalid data or a malfunctioning
            # converter does not crash the item view (otherwise a user might
            # not be able to fix it from the UI).
            error_id = uuid.uuid4()
            logging.exception(f"An exception happened in _render_data (error_id = {error_id} ):")
            rendered_data = render_template(
                "crash.html", server_time=time.strftime("%Y-%m-%d %H:%M:%S %Z"), url=request.url, error_id=error_id
            )
        return rendered_data

    def _render_data_xml(self):
        doc = self.internal_representation()
        return conv_serialize(doc, {moin_page.namespace: "", xlink.namespace: "xlink", html.namespace: "html"}, "xml")

    def _render_data_highlight(self):
        # override this in child classes
        return ""

    def _get_data_diff_text(self, oldfile, newfile):
        """Get the text diff of 2 versions of file contents

        :param oldfile: file that contains old content data (bytes)
        :param newfile: file that contains new content data (bytes)
        :return: list of diff lines in a unified format without trailing linefeeds
        """
        return []

    def _render_data_slide(self, preview=None):
        try:
            from moin.converters import default_registry as reg

            doc = self.internal_representation(preview=preview)
            doc = self._expand_document(doc)

            slide_pages = []
            before_first_header = True
            for elem1 in doc:
                single_slide = []
                for element in elem1:
                    if element.tag.name == "h" and element.get(moin_page("outline-level")) in ["1", "2"]:
                        if before_first_header:
                            before_first_header = False  # ignore everything before
                        else:
                            slide_pages.append(single_slide)
                        single_slide = []
                    single_slide.append(element)
                slide_pages.append(single_slide)
            print(f"{len(slide_pages)} slides found.")

            flaskg.clock.start("conv_dom_html")
            html_conv = reg.get(type_moin_document, Type("application/x-xhtml-moin-page"))

            slide_content = []
            attrib = {moin_page.class_: "moin-slides"}
            for slide in slide_pages:
                slide_content.append(moin_page.div(attrib=attrib, children=slide))

            body = moin_page.body(children=slide_content)
            root = moin_page.page(children=[body])
            doc = html_conv(root)
            rendered_data = conv_serialize(doc, {html.namespace: ""})
            flaskg.clock.stop("conv_dom_html")

        except Exception:
            # we really want to make sure that invalid data or a malfunctioning
            # converter does not crash the item view (otherwise a user might
            # not be able to fix it from the UI).
            error_id = uuid.uuid4()
            logging.exception(f"An exception happened in _render_data (error_id = {error_id} ):")
            rendered_data = [
                render_template(
                    "crash.html", server_time=time.strftime("%Y-%m-%d %H:%M:%S %Z"), url=request.url, error_id=error_id
                )
            ]
        return rendered_data

    def get_templates(self, contenttype=None):
        """create a list of templates (for some specific contenttype)"""
        terms = [
            Term(WIKINAME, app.cfg.interwikiname),
            Term(TAGS, TEMPLATE),
            Term(NAMESPACE, self.item.fqname.namespace),
        ]
        if contenttype is not None:
            terms.append(Term(CONTENTTYPE, contenttype))
        query = And(terms)
        revs = flaskg.storage.search(query, sortedby=NAME_EXACT, limit=None)
        return [rev.fqname.fullname for rev in revs]


@register
class NonExistentContent(Content):
    """Dummy Content to use with NonExistent."""

    contenttype = CONTENTTYPE_NONEXISTENT
    group = None

    def do_get(self, force_attachment=False, mimetype=None):
        abort(404)

    def _convert(self, doc):
        abort(404)


@register
class Binary(Content):
    """An arbitrary binary item, fallback class for every item mimetype."""

    contenttype = "*/*"

    # XXX reads item rev data into memory!
    def get_data(self):
        if self.rev is not None:
            return self.rev.data.read()
        else:
            return ""

    data = property(fget=get_data)

    class ModifyForm(Form):
        """
        The content part of the ModifyForm of an Item subclass. See also the
        doc of Item._ModifyForm.
        """

        template = "modify_binary.html"
        data_file = File.using(optional=True, label=L_("Replace content with uploaded file:"))

        def _load(self, item):
            pass

        def _dump(self, item):
            data_file = self["data_file"].value
            if data_file:
                data = data_file.stream
                # this is likely a guess by the browser, based on the filename
                contenttype_guessed = data_file.content_type  # comes from form multipart data
                return data, contenttype_guessed
            else:
                return None, None

    def _render_data_diff(self, oldrev, newrev, rev_links={}, fqname=None):
        hash_name = HASH_ALGORITHM
        if oldrev.meta[hash_name] == newrev.meta[hash_name]:
            return _("The items have the same data hash code (that means they very likely have the same data).")
        else:
            return _("The items have different data.")

    _render_data_diff_text = _render_data_diff
    _render_data_diff_raw = _render_data_diff

    def _render_data_diff_atom(self, oldrev, newrev):
        return render_template(
            "atom.html", oldrev=oldrev, newrev=newrev, get="binary", content=Markup(self._render_data())
        )

    def _convert(self, doc):
        return _("Impossible to convert the data to the contenttype: {contenttype}").format(
            contenttype=request.values.get("contenttype")
        )

    def do_get(self, force_attachment=False, mimetype=None):
        hash = self.rev.meta.get(HASH_ALGORITHM)
        if is_resource_modified(request.environ, hash):  # use hash as etag
            return self._do_get_modified(hash, force_attachment=force_attachment, mimetype=mimetype)
        else:
            return Response(status=304)

    def _do_get_modified(self, hash, force_attachment=False, mimetype=None):
        member = request.values.get("member")
        return self._do_get(hash, member, force_attachment=force_attachment, mimetype=mimetype)

    def _do_get(self, hash, member=None, force_attachment=False, mimetype=None):
        if member:  # content = file contained within a archive item revision
            path, filename = os.path.split(member)
            mt = MimeType(filename=filename)
            file_to_send = self.get_member(member)
            # force attachment download, so it uses attachment_filename
            # otherwise it will use the itemname from the URL for saving
            force_attachment = True
        else:  # content = item revision
            rev = self.rev
            filename = get_download_file_name(rev.item.fqname)
            try:
                mimestr = rev.meta[CONTENTTYPE]
            except KeyError:
                mt = MimeType(filename=filename)
            else:
                mt = MimeType(mimestr=mimestr)
            file_to_send = rev.data
        if mimetype:
            content_type = mimetype
        else:
            content_type = mt.content_type()
        as_attachment = force_attachment or mt.as_attachment(app.cfg)
        return send_file(
            file=file_to_send,
            mimetype=content_type,
            as_attachment=as_attachment,
            attachment_filename=filename,
            cache_timeout=10,  # wiki data can change rapidly
            add_etags=True,
            etag=hash,
            conditional=True,
        )


@register
class OctetStream(Binary):
    """
    Fallback Content for uploaded file of unknown contenttype.
    """

    contenttype = "application/octet-stream"
    display_name = "Binary File"


class RenderableBinary(Binary):
    """Base class for some binary stuff that renders with a object tag."""


class Application(Binary):
    """Base class for application/*"""


class TarMixin:
    """
    TarMixin offers additional functionality for tar-like items to list and
    access member files and to create new revisions by multiple posts.
    """

    def list_members(self):
        """
        list tar file contents (member file names)
        """
        self.rev.data.seek(0)
        tf = tarfile.open(fileobj=self.rev.data, mode="r")
        return tf.getnames()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        :param name: name of the data in the container file
        """
        self.rev.data.seek(0)
        tf = tarfile.open(fileobj=self.rev.data, mode="r")
        return tf.extractfile(name)

    def put_member(self, name, content, content_length, expected_members):
        """
        puts a new member file into a temporary tar container.
        If all expected members have been put, it saves the tar container
        to a new item revision.

        :param name: name of the data in the container file
        :param content: the data to store into the tar file (bytes or file-like)
        :param content_length: byte-length of content (for bytes, None can be given)
        :param expected_members: set of expected member file names
        """
        if name not in expected_members:
            raise StorageError(f"tried to add unexpected member {name!r} to container item {self.name!r}")
        assert isinstance(name, str)
        temp_fname = os.path.join(
            tempfile.gettempdir(), "TarContainer_" + cache_key(usage="TarContainer", name=self.name)
        )
        with tarfile.open(temp_fname, mode="a") as tf:
            ti = tarfile.TarInfo(name)
            if isinstance(content, bytes):
                if content_length is None:
                    content_length = len(content)
                content = BytesIO(content)  # we need a file obj
            elif not hasattr(content, "read"):
                logging.error(f"unsupported content object: {content!r}")
                raise StorageError(f"unsupported content object: {content!r}")
            else:
                raise NotImplementedError
            assert content_length >= 0  # we don't want -1 interpreted as 4G-1
            ti.size = content_length
            tf.addfile(ti, content)
            tf_members = set(tf.getnames())
        if tf_members - expected_members:
            msg = f"found unexpected members in container item {self.name!r}"
            logging.error(msg)
            os.remove(temp_fname)
            raise StorageError(msg)
        if tf_members == expected_members:
            # everything we expected has been added to the tar file, save the container as revision
            meta = {CONTENTTYPE: self.contenttype}
            with open(temp_fname, "rb") as data:
                self.item._save(meta, data, names=self.name, action=ACTION_SAVE, comment="")
            os.remove(temp_fname)


@register
class ApplicationXTar(TarMixin, Application):
    """
    Tar items
    """

    contenttype = "application/x-tar"
    display_name = "TAR"


@register
class ApplicationXGTar(ApplicationXTar):
    """
    Compressed tar items
    """

    contenttype = "application/x-gtar"
    display_name = "TGZ"


class ZipMixin:
    """
    ZipMixin offers additional functionality for zip-like items to list and
    access member files.
    """

    def list_members(self):
        """
        list zip file contents (member file names)
        """
        self.rev.data.seek(0)
        zf = zipfile.ZipFile(self.rev.data, mode="r")
        return zf.namelist()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        :param name: name of the data in the zip file
        """
        self.rev.data.seek(0)
        zf = zipfile.ZipFile(self.rev.data, mode="r")
        return zf.open(name, mode="r")

    def put_member(self, name, content, content_length, expected_members):
        raise NotImplementedError


@register
class ApplicationZip(ZipMixin, Application):
    """
    Zip items
    """

    contenttype = "application/zip"
    display_name = "ZIP"


@register
class PDF(Application):
    """PDF"""

    contenttype = "application/pdf"
    display_name = "PDF"


@register
class Video(Binary):
    """Base class for video/*"""

    contenttype = "video/*"
    group = GROUP_VIDEO


@register
class OGGVideo(Video):
    contenttype = "video/ogg"
    display_name = "OGG"


@register
class WebMVideo(Video):
    contenttype = "video/webm"
    display_name = "WebM"


@register
class MP4(Video):
    contenttype = "video/mp4"
    display_name = "MP4"


@register
class Audio(Binary):
    """Base class for audio/*"""

    contenttype = "audio/*"
    group = GROUP_AUDIO


@register
class WAV(Audio):
    contenttype = "audio/x-wav"
    display_name = "WAV"


@register
class OGGAudio(Audio):
    contenttype = "audio/ogg"
    display_name = "OGG"


@register
class MP3(Audio):
    contenttype = "audio/mpeg"
    display_name = "MP3"


@register
class WebMAudio(Audio):
    contenttype = "audio/webm"
    display_name = "WebM"


@register
class Image(Binary):
    """Base class for image/*"""

    contenttype = "image/*"


class RenderableImage(RenderableBinary):
    """Base class for renderable Image mimetypes"""

    group = GROUP_IMAGE


@register
class SvgImage(RenderableImage):
    """SVG images use <object> tag mechanism from RenderableBinary base class"""

    contenttype = "image/svg+xml"
    display_name = "SVG"


class RenderableBitmapImage(RenderableImage):
    """PNG/JPEG/GIF images use <img> tag (better browser support than <object>)"""

    # if mimetype is also transformable, please register in TransformableImage ONLY!


class TransformableBitmapImage(RenderableBitmapImage):
    """We can transform (resize, rotate, mirror) some image types"""

    def _transform(self, content_type, size=None, transpose_op=None):
        """resize to new size (optional), transpose according to exif infos,
        result data should be content_type.
        """
        try:
            from PIL import Image as PILImage
        except ImportError:
            # no PIL, we can't do anything, we just output the revision data as is
            return content_type, self.rev.data.read()

        if content_type == "image/jpeg":
            output_type = "JPEG"
        elif content_type == "image/png":
            output_type = "PNG"
        elif content_type == "image/gif":
            output_type = "GIF"
        else:
            raise ValueError(f"content_type {content_type!r} not supported")

        # revision obj has read() seek() tell(), thus this works:
        image = PILImage.open(self.rev.data)
        image.load()

        try:
            # if we have EXIF data, we can transpose (e.g. rotate left),
            # so the rendered image is correctly oriented:
            transpose_op = transpose_op or 1  # or self.exif['Orientation']
        except KeyError:
            transpose_op = 1  # no change

        if size is not None:
            image = image.copy()  # create copy first as thumbnail works in-place
            image.thumbnail(size, PILImage.LANCZOS)

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

        outfile = BytesIO()
        image.save(outfile, output_type)
        data = outfile.getvalue()
        outfile.close()
        return content_type, data

    def _do_get_modified(self, hash, force_attachment=False, mimetype=None):
        try:
            width = int(request.values.get("w"))
        except (TypeError, ValueError):
            width = None
        try:
            height = int(request.values.get("h"))
        except (TypeError, ValueError):
            height = None
        try:
            transpose = int(request.values.get("t"))
            assert 1 <= transpose <= 8
        except (TypeError, ValueError, AssertionError):
            transpose = 1
        if width or height or transpose != 1:
            # resize requested, XXX check ACL behaviour! XXX
            hash_name = HASH_ALGORITHM
            hash_hexdigest = self.rev.meta[hash_name]
            cid = cache_key(
                usage="ImageTransform",
                hash_name=hash_name,
                hash_hexdigest=hash_hexdigest,
                width=width,
                height=height,
                transpose=transpose,
            )
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
            return super()._render_data_diff_atom(oldrev, newrev)
        url = url_for("frontend.diffraw", _external=True, item_name=self.name, rev1=oldrev.revid, rev2=newrev.revid)
        return render_template(
            "atom.html", oldrev=oldrev, newrev=newrev, get="binary", content=Markup(f'<img src="{escape(url)}" />')
        )

    def _render_data_diff(self, oldrev, newrev, rev_links={}, fqname=None):
        if PIL is None:
            # no PIL, we can't do anything, we just call the base class method
            return super()._render_data_diff(oldrev, newrev)
        url = url_for("frontend.diffraw", item_name=self.name, rev1=oldrev.revid, rev2=newrev.revid)
        return Markup(f'<img src="{escape(url)}" />')

    def _render_data_diff_raw(self, oldrev, newrev):
        hash_name = HASH_ALGORITHM
        cid = cache_key(
            usage="ImageDiff", hash_name=hash_name, hash_old=oldrev.meta[hash_name], hash_new=newrev.meta[hash_name]
        )
        c = app.cache.get(cid)
        if c is None:
            if PIL is None:
                abort(404)  # TODO render user friendly error image

            content_type = newrev.meta[CONTENTTYPE]
            if content_type == "image/jpeg":
                output_type = "JPEG"
            elif content_type == "image/png":
                output_type = "PNG"
            elif content_type == "image/gif":
                output_type = "GIF"
            else:
                raise ValueError(f"content_type {content_type!r} not supported")

            try:
                oldimage = PILImage.open(oldrev.data)
                newimage = PILImage.open(newrev.data)
                oldimage.load()
                newimage.load()
                diffimage = PILdiff(newimage, oldimage)
                outfile = BytesIO()
                diffimage.save(outfile, output_type)
                data = outfile.getvalue()
                outfile.close()
                headers = wikiutil.file_headers(content_type=content_type, content_length=len(data))
                app.cache.set(cid, (headers, data))
            except (OSError, ValueError) as err:
                logging.exception(f"error during PILdiff: {err}")
                abort(404)  # TODO render user friendly error image
        else:
            # XXX TODO check ACL behaviour
            headers, data = c
        return Response(data, headers=headers)

    def _render_data_diff_text(self, oldrev, newrev):
        return super()._render_data_diff_text(oldrev, newrev)


@register
class PNG(TransformableBitmapImage):
    """PNG image."""

    contenttype = "image/png"
    display_name = "PNG"


@register
class JPEG(TransformableBitmapImage):
    """JPEG image."""

    contenttype = "image/jpeg"
    display_name = "JPEG"


@register
class GIF(TransformableBitmapImage):
    """GIF image."""

    contenttype = "image/gif"
    display_name = "GIF"


@register
class Text(Binary):
    """Base class for text/*"""

    contenttype = "text/*"
    default_contenttype_params = dict(charset="utf-8")
    group = GROUP_OTHER_TEXT

    class ModifyForm(Binary.ModifyForm):
        template = "modify_text.html"
        data_text = String.using(strip=False, optional=True).with_properties(placeholder=L_("Type your text here"))
        rows = ROWS_DATA
        cols = COLS

        def _load(self, item):
            super()._load(item)
            data = item.data
            data = item.data_storage_to_internal(data)
            data = item.data_internal_to_form(data)
            self["data_text"] = data

        def _dump(self, item):
            data, contenttype_guessed = super()._dump(item)
            if data is None:
                data = self["data_text"].value
                data = item.data_form_to_internal(data)
                data = item.data_internal_to_storage(data)
                # we know it is text and utf-8 - XXX is there a way to get the charset of the form?
                contenttype_guessed = "text/plain;charset=utf-8"
            return data, contenttype_guessed

    # text/plain mandates crlf - but in memory, we want lf only
    def data_internal_to_form(self, text):
        """convert data from memory format to form format"""
        return text.replace("\n", "\r\n")

    def data_form_to_internal(self, data):
        """convert data from form format to memory format"""
        return data.replace("\r\n", "\n")

    def data_internal_to_storage(self, text):
        """convert data from memory format to storage format"""
        return text.replace("\n", "\r\n").encode(CHARSET)

    def data_storage_to_internal(self, data):
        """convert data from storage format to memory format"""
        return data.decode(CHARSET).replace("\r\n", "\n")

    def _render_data_diff_html(self, oldrev, newrev, template, rev_links={}, fqname=None):
        """Render HTML formatted meta and content diff of 2 revisions

        :param oldrev: old revision object
        :param newrev: new revision object
        :param template: name of the template to be rendered
        :return: HTML data with meta and content diff
        """
        from moin.items import Item  # XXX causes import error if placed near top

        diffs = self._get_data_diff_html(oldrev.data, newrev.data)
        item = Item.create(fqname.fullname, rev_id=newrev.meta["revid"])
        rendered = Markup(item.content._render_data())
        return render_template(
            template,
            item_name=fqname.fullname,
            oldrev=oldrev,
            newrev=newrev,
            diffs=diffs,
            rendered=rendered,
            rev_links=rev_links,
        )

    def _get_data_diff_html(self, oldfile, newfile):
        """Get the HTML diff of 2 versions of file contents

        :param oldfile: file that contains old content data (bytes)
        :param newfile: file that contains new content data (bytes)
        :return: list of tuples of the format (left lineno, deleted Markup content,
                 right lineno, added Markup content)
        """
        old_text = self.data_storage_to_internal(oldfile.read())
        new_text = self.data_storage_to_internal(newfile.read())
        return [(d[0], Markup(d[1]), d[2], Markup(d[3])) for d in html_diff(old_text, new_text)]

    def _get_data_diff_text(self, oldfile, newfile):
        """Get the text diff of 2 versions of file contents

        :param oldfile: file that contains old content data (bytes)
        :param newfile: file that contains new content data (bytes)
        :return: list of diff lines in a unified format without trailing linefeeds
        """
        old_text = self.data_storage_to_internal(oldfile.read())
        new_text = self.data_storage_to_internal(newfile.read())
        return text_diff(old_text.splitlines(), new_text.splitlines())

    def _render_data_diff_atom(self, oldrev, newrev, fqname=None):
        """renders diff in HTML for atom feed"""
        return self._render_data_diff_html(oldrev, newrev, "diff_text_atom.html", fqname=fqname)

    def _render_data_diff(self, oldrev, newrev, rev_links={}, fqname=None):
        return self._render_data_diff_html(oldrev, newrev, "diff_text.html", rev_links=rev_links, fqname=fqname)

    def _render_data_diff_text(self, oldrev, newrev):
        """Render text diff of 2 revisions' contents

        :param oldrev: old revision object
        :param newrev: new revision object
        :return: text data of a content diff
        """
        difflines = self._get_data_diff_text(oldrev.data, newrev.data)
        return "\n".join(difflines)

    _render_data_diff_raw = _render_data_diff

    def _render_data_highlight(self):
        from moin.converters import default_registry as reg

        data_text = self.data_storage_to_internal(self.data)
        # TODO: use registry as soon as it is in there
        from moin.converters.pygments_in import Converter as PygmentsConverter

        pygments_conv = PygmentsConverter(contenttype=self.contenttype)
        doc = pygments_conv(data_text)
        # TODO: Real output format
        html_conv = reg.get(type_moin_document, Type("application/x-xhtml-moin-page"))
        doc = html_conv(doc)
        return conv_serialize(doc, {html.namespace: ""})


class MarkupItem(Text):
    """
    some kind of item with markup
    (internal links and transcluded items)
    """

    group = GROUP_MARKUP_TEXT


@register
class MoinWiki(MarkupItem):
    """MoinMoin wiki markup"""

    contenttype = "text/x.moin.wiki"
    display_name = "MoinMoin"


@register
class CreoleWiki(MarkupItem):
    """Creole wiki markup"""

    contenttype = "text/x.moin.creole"
    display_name = "Creole"


@register
class MediaWiki(MarkupItem):
    """MediaWiki markup"""

    contenttype = "text/x-mediawiki"
    display_name = "MediaWiki"


@register
class ReST(MarkupItem):
    """ReStructured Text markup"""

    contenttype = "text/x-rst"
    display_name = "ReST"


@register
class Markdown(MarkupItem):
    """Markdown markup"""

    contenttype = "text/x-markdown"
    display_name = "Markdown"


@register
class HTML(MarkupItem):
    """
    HTML markup

    Note: As we use html_in converter to convert this to DOM and later some
          output converterter to produce output format (e.g. html_out for html
          output), all(?) unsafe stuff will get lost.

    Note: If raw revision data is accessed, unsafe stuff might be present!
    """

    contenttype = "text/html"
    display_name = "HTML"

    class ModifyForm(Text.ModifyForm):
        template = "modify_text_html.html"


@register
class DocBook(MarkupItem):
    """DocBook Document"""

    contenttype = "application/docbook+xml"
    display_name = "DocBook"

    def _convert(self, doc):
        from emeraldtree import ElementTree as ET
        from moin.converters import default_registry as reg

        doc = self._expand_document(doc)

        # We convert the internal representation of the document
        # into a DocBook document
        conv = reg.get(type_moin_document, Type("application/docbook+xml"))

        doc = conv(doc)

        # We determine the different namespaces of the output form
        output_namespaces = {docbook.namespace: "", xlink.namespace: "xlink"}

        # We convert the result into a BytesIO object
        # With the appropriate namespace
        # TODO: Some other operation should probably be done here too
        # like adding a doctype
        file_to_send = BytesIO()
        tree = ET.ElementTree(doc)
        tree.write(file_to_send, namespaces=output_namespaces)

        # We determine the different parameters for the reply
        mt = MimeType(mimestr="application/docbook+xml;charset=utf-8")
        content_type = mt.content_type()
        as_attachment = mt.as_attachment(app.cfg)
        # After creation of the BytesIO, we are at the end of the file
        # so position is the size the file.
        # and then we should move it back at the beginning of the file
        file_to_send.seek(0)
        # Important: empty filename keeps flask from trying to autodetect filename,
        # as this would not work for us, because our file's are not necessarily fs files.
        return send_file(
            file=file_to_send,
            mimetype=content_type,
            as_attachment=as_attachment,
            attachment_filename=None,
            cache_timeout=10,  # wiki data can change rapidly
            add_etags=False,
            etag=None,
            conditional=True,
        )


@register
class PlainText(Text):
    contenttype = "text/plain"
    display_name = "Plain Text"


@register
class Diff(Text):
    contenttype = "text/x-diff"
    display_name = "Diff/Patch"


@register
class PythonCode(Text):
    contenttype = "text/x-python"
    display_name = "Python Code"


@register
class CSV(Text):
    contenttype = "text/csv"
    display_name = "CSV"


@register
class IRCLog(Text):
    contenttype = "text/x-irclog"
    display_name = "IRC Log"


class Draw(TarMixin, Image):
    """
    Base class for drawing apps that use special Java/Javascript applets to modify and store data in a tar file.
    """

    group = GROUP_DRAWING

    class ModifyForm(Binary.ModifyForm):
        # Set the workaround flag respected in modify.html
        is_draw = True

    def handle_post(self):
        raise NotImplementedError


class DrawPNGMap(Draw):
    """
    Base class for drawings that have a png with click map
    """

    def _read_map(self):
        mapfile = self.get_member("drawing.map")
        try:
            image_map = mapfile.read()
            mapfile.close()
        except OSError:
            image_map = ""
        return image_map

    def _transform_map(self, image_map, title):
        raise NotImplementedError

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        png_url = url_for("frontend.get_item", item_name=self.name, member="drawing.png", rev=self.rev.revid)
        title = _("Edit drawing {filename} (opens in new window)").format(filename=self.name)
        image_map = self._read_map()
        if image_map:
            mapid, image_map = self._transform_map(image_map, title)
            title = _("Clickable drawing: {filename}").format(filename=self.name)
            return Markup(image_map + f'<img src="{png_url}" alt="{title}" usemap="#{mapid}" />')
        else:
            return Markup(f'<img src="{png_url}" alt="{title}" />')


@register
class SvgDraw(Draw):
    """drawings by svg-edit. It creates two files (svg, png) which are stored as tar file."""

    contenttype = "application/x-svgdraw"
    display_name = "SVGDRAW"

    class ModifyForm(Draw.ModifyForm):
        template = "modify_svg-edit.html"

    def handle_post(self):
        # called from modify UI/POST
        png_upload = request.values.get("png_data")
        svg_upload = request.values.get("filepath")
        png_content = png_upload.decode("base_64")
        png_content = base64.urlsafe_b64decode(png_content.split(",")[1])
        svg_content = svg_upload.decode("base_64")
        content_length = None
        self.put_member("drawing.svg", svg_content, content_length, expected_members={"drawing.svg", "drawing.png"})
        self.put_member("drawing.png", png_content, content_length, expected_members={"drawing.svg", "drawing.png"})

    def _render_data(self):
        # TODO: this could be a converter -> dom, then transcluding this kind
        # of items and also rendering them with the code in base class could work
        drawing_url = url_for("frontend.get_item", item_name=self.name, member="drawing.svg", rev=self.rev.revid)
        png_url = url_for("frontend.get_item", item_name=self.name, member="drawing.png", rev=self.rev.revid)
        return Markup(f'<img src="{png_url}" alt="{drawing_url}" />')
