# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Archives converter (e.g. zip, tar)

Make a DOM Tree representation of an archive (== list contents of it in a table).
"""


from datetime import datetime
import tarfile
import zipfile

from . import default_registry
from ._table import TableMixin

from moin.i18n import _
from moin.utils import utcfromtimestamp
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.utils.mime import Type, type_moin_document
from moin.utils.interwiki import CompositeName
from moin.constants.keys import NAME, NAMESPACE, NAME_EXACT

from moin import log

logging = log.getLogger(__name__)


class ArchiveException(Exception):
    """
    exception class used in case of trouble with opening/listing an archive
    """


class ArchiveConverter(TableMixin):
    """
    Base class for archive converters, convert an archive to a DOM table
    with an archive listing.
    """

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def process_name(self, member_name):
        attrib = {
            xlink.href: Iri(scheme="wiki", authority="", path="/" + self.fullname, query=f"do=get&member={member_name}")
        }
        return moin_page.a(attrib=attrib, children=[member_name])

    def process_datetime(self, dt):
        return str(dt.isoformat(" "))

    def process_size(self, size):
        return str(size)

    def __call__(self, rev, contenttype=None, arguments=None):
        fqname = CompositeName(rev.meta[NAMESPACE], NAME_EXACT, rev.meta[NAME][0])
        self.fullname = fqname.fullname
        try:
            contents = self.list_contents(rev.data)
            contents = [
                (self.process_size(size), self.process_datetime(dt), self.process_name(name))
                for size, dt, name in contents
            ]
            table = self.build_dom_table(contents, head=[_("Size"), _("Timestamp"), _("Name")], cls="zebra")
            body = moin_page.body(children=(table,))
            return moin_page.page(children=(body,))
        except ArchiveException as err:
            logging.exception("An exception within archive file handling occurred:")
            # XXX we also use a table for error reporting, could be
            # something more adequate, though:
            return self.build_dom_table([[str(err)]])

    def list_contents(self, fileobj):
        """
        analyze archive we get as fileobj and return data for table rendering.

        We return a list of rows, each row is a list of cells.

        Usually each row is [size, datetime, name] for each archive member.

        In case of problems, it shall raise ArchiveException(error_msg).
        """
        raise NotImplementedError


class TarConverter(ArchiveConverter):
    """
    Support listing tar files.
    """

    def list_contents(self, fileobj):
        try:
            rows = []
            tf = tarfile.open(fileobj=fileobj, mode="r")
            for tinfo in tf.getmembers():
                if tinfo.isfile():
                    # display only normal files, not directories
                    rows.append((tinfo.size, utcfromtimestamp(tinfo.mtime), tinfo.name))
            return rows
        except tarfile.TarError as err:
            raise ArchiveException(str(err))


class ZipConverter(ArchiveConverter):
    """
    Support listing zip files.
    """

    def list_contents(self, fileobj):
        try:
            rows = []
            zf = zipfile.ZipFile(fileobj, mode="r")
            for zinfo in zf.filelist:
                if not (zinfo.file_size == 0 and zinfo.filename.endswith("/")):
                    # display only normal files, not directories
                    rows.append((zinfo.file_size, datetime(*zinfo.date_time), zinfo.filename))  # y,m,d,h,m,s
            return rows
        except (RuntimeError, zipfile.BadZipfile) as err:
            # RuntimeError is raised by zipfile stdlib module in case of
            # problems (like inconsistent slash and backslash usage in the
            # archive or a defective zip file).
            raise ArchiveException(str(err))


default_registry.register(TarConverter._factory, Type("application/x-tar"), type_moin_document)
default_registry.register(TarConverter._factory, Type("application/x-gtar"), type_moin_document)
default_registry.register(ZipConverter._factory, Type("application/zip"), type_moin_document)
