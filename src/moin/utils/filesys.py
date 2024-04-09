# Copyright: 2002 Juergen Hermann <jh@web.de>
# Copyright: 2006-2010 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - File System Utilities
"""


import sys
import os
import shutil
import time
import errno

from glob import glob
from stat import S_ISDIR, ST_MODE, S_IMODE
from os import replace as rename

from moin import log

logging = log.getLogger(__name__)


#############################################################################
# Misc Helpers
#############################################################################


def chmod(name, mode, catchexception=True):
    """change mode of some file/dir on platforms that support it."""
    try:
        os.chmod(name, mode)
    except OSError:
        if not catchexception:
            raise


rename_overwrite = rename


def rename_no_overwrite(oldname, newname, delete_old=False):
    """Multiplatform rename

    This kind of rename is doing things differently: it fails if newname
    already exists. This is the usual thing on win32, but not on posix.

    If delete_old is True, oldname is removed in any case (even if the
    rename did not succeed).
    """
    if os.name == "nt":
        try:
            try:
                os.rename(oldname, newname)
                success = True
            except Exception:
                success = False
                raise
        finally:
            if not success and delete_old:
                os.unlink(oldname)
    else:
        try:
            try:
                os.link(oldname, newname)
                success = True
            except Exception:
                success = False
                raise
        finally:
            if success or delete_old:
                os.unlink(oldname)


def touch(name):
    if sys.platform == "win32":
        import win32file
        import win32con
        import pywintypes

        access = win32file.GENERIC_WRITE
        share = win32file.FILE_SHARE_DELETE | win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE
        create = win32file.OPEN_EXISTING
        mtime = time.gmtime()
        handle = win32file.CreateFile(
            name,
            access,
            share,
            None,
            create,
            win32file.FILE_ATTRIBUTE_NORMAL | win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
        try:
            newTime = pywintypes.Time(mtime)
            win32file.SetFileTime(handle, newTime, newTime, newTime)
        finally:
            win32file.CloseHandle(handle)
    else:
        os.utime(name, None)


def access_denied_decorator(fn):
    """Due to unknown reasons, some os.* functions on Win32 sometimes fail
    with Access Denied (although access should be possible).
    Just retrying it a bit later works and this is what we do.
    """
    if sys.platform == "win32":

        def wrapper(*args, **kwargs):
            max_retries = 42
            retry = 0
            while True:
                try:
                    return fn(*args, **kwargs)
                except OSError as err:
                    retry += 1
                    if retry > max_retries:
                        raise
                    if err.errno == errno.EACCES:
                        logging.warning(f"{fn.__name__}({args!r}, {kwargs!r}) -> access denied. retrying...")
                        time.sleep(0.01)
                        continue
                    raise

        return wrapper
    else:
        return fn


stat = access_denied_decorator(os.stat)
mkdir = access_denied_decorator(os.mkdir)
rmdir = access_denied_decorator(os.rmdir)


def copystat(src, dst):
    """Copy stat bits from src to dst

    This should be used when shutil.copystat would be used on directories
    on win32 because win32 does not support utime() for directories.

    According to the official docs written by Microsoft, it returns ENOACCES if the
    supplied filename is a directory. Looks like a trainee implemented the function.
    """
    if sys.platform == "win32" and S_ISDIR(os.stat(dst)[ST_MODE]):
        if os.name == "nt":
            st = os.stat(src)
            mode = S_IMODE(st[ST_MODE])
            if hasattr(os, "chmod"):
                os.chmod(dst, mode)  # KEEP THIS ONE!
    else:
        shutil.copystat(src, dst)


def copytree(src, dst, symlinks=False):
    """Recursively copy a directory tree using copy2().

    The destination directory must not already exist.
    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    In contrary to shutil.copytree, this version also copies directory
    stats, not only file stats.

    """
    names = os.listdir(src)
    os.mkdir(dst)
    copystat(src, dst)
    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks)
            else:
                shutil.copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except OSError as why:
            errors.append((srcname, dstname, why))
    if errors:
        raise OSError(str(errors))


def wiki_index_exists():
    """Return true if a wiki index exists."""
    logging.debug("CWD: %s", os.getcwd())
    return bool(glob("wiki/index/_all_revs_*.toc"))
