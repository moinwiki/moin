# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - File System Utilities

    @copyright: 2002 Juergen Hermann <jh@web.de>,
                2006-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import sys, os, shutil, time, errno
from stat import S_ISDIR, ST_MODE, S_IMODE
import warnings

from MoinMoin import log
logging = log.getLogger(__name__)

#############################################################################
### Misc Helpers
#############################################################################

def chmod(name, mode, catchexception=True):
    """ change mode of some file/dir on platforms that support it.
        usually you don't need this because we use os.umask() in app init
    """
    try:
        os.chmod(name, mode)
    except OSError:
        if not catchexception:
            raise


from werkzeug.posixemulation import *

rename_overwrite = rename

def rename_no_overwrite(oldname, newname, delete_old=False):
    """ Multiplatform rename

    This kind of rename is doing things differently: it fails if newname
    already exists. This is the usual thing on win32, but not on posix.

    If delete_old is True, oldname is removed in any case (even if the
    rename did not succeed).
    """
    if os.name == 'nt':
        try:
            try:
                os.rename(oldname, newname)
                success = True
            except:
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
            except:
                success = False
                raise
        finally:
            if success or delete_old:
                os.unlink(oldname)


def touch(name):
    if sys.platform == 'win32':
        import win32file, win32con, pywintypes

        access = win32file.GENERIC_WRITE
        share = (win32file.FILE_SHARE_DELETE |
                 win32file.FILE_SHARE_READ |
                 win32file.FILE_SHARE_WRITE)
        create = win32file.OPEN_EXISTING
        mtime = time.gmtime()
        handle = win32file.CreateFile(name, access, share, None, create,
                                      win32file.FILE_ATTRIBUTE_NORMAL |
                                      win32con.FILE_FLAG_BACKUP_SEMANTICS,
                                      None)
        try:
            newTime = pywintypes.Time(mtime)
            win32file.SetFileTime(handle, newTime, newTime, newTime)
        finally:
            win32file.CloseHandle(handle)
    else:
        os.utime(name, None)


def access_denied_decorator(fn):
    """ Due to unknown reasons, some os.* functions on Win32 sometimes fail
        with Access Denied (although access should be possible).
        Just retrying it a bit later works and this is what we do.
    """
    if sys.platform == 'win32':
        def wrapper(*args, **kwargs):
            max_retries = 42
            retry = 0
            while True:
                try:
                    return fn(*args, **kwargs)
                except OSError, err:
                    retry += 1
                    if retry > max_retries:
                        raise
                    if err.errno == errno.EACCES:
                        logging.warning('%s(%r, %r) -> access denied. retrying...' % (fn.__name__, args, kwargs))
                        time.sleep(0.01)
                        continue
                    raise
        return wrapper
    else:
        return fn

stat = access_denied_decorator(os.stat)
mkdir = access_denied_decorator(os.mkdir)
rmdir = access_denied_decorator(os.rmdir)


def fuid(filename, max_staleness=3600):
    """ return a unique id for a file

        Using just the file's mtime to determine if the file has changed is
        not reliable - if file updates happen faster than the file system's
        mtime granularity, then the modification is not detectable because
        the mtime is still the same.

        This function tries to improve by using not only the mtime, but also
        other metadata values like file size and inode to improve reliability.

        For the calculation of this value, we of course only want to use data
        that we can get rather fast, thus we use file metadata, not file data
        (file content).

        Note: depending on the operating system capabilities and the way the
              file update is done, this function might return the same value
              even if the file has changed. It should be better than just
              using file's mtime though.
              max_staleness tries to avoid the worst for these cases.

        @param filename: file name of the file to look at
        @param max_staleness: if a file is older than that, we may consider
                              it stale and return a different uid - this is a
                              dirty trick to work around changes never being
                              detected. Default is 3600 seconds, use None to
                              disable this trickery. See below for more details.
        @return: an object that changes value if the file changed,
                 None is returned if there were problems accessing the file
    """
    try:
        st = os.stat(filename)
    except (IOError, OSError):
        uid = None  # for permanent errors on stat() this does not change, but
                    # having a changing value would be pointless because if we
                    # can't even stat the file, it is unlikely we can read it.
    else:
        fake_mtime = int(st.st_mtime)
        if not st.st_ino and max_staleness:
            # st_ino being 0 likely means that we run on a platform not
            # supporting it (e.g. win32) - thus we likely need this dirty
            # trick
            now = int(time.time())
            if now >= st.st_mtime + max_staleness:
                # keep same fake_mtime for each max_staleness interval
                fake_mtime = int(now / max_staleness) * max_staleness
        uid = (st.st_mtime,  # might have a rather rough granularity, e.g. 2s
                             # on FAT, 1s on ext3 and might not change on fast
                             # updates
               st.st_ino,  # inode number (will change if the update is done
                           # by e.g. renaming a temp file to the real file).
                           # not supported on win32 (0 ever)
               st.st_size,  # likely to change on many updates, but not
                            # sufficient alone
               fake_mtime,  # trick to workaround file system / platform
                            # limitations causing permanent trouble
              )
    return uid


def copystat(src, dst):
    """Copy stat bits from src to dst

    This should be used when shutil.copystat would be used on directories
    on win32 because win32 does not support utime() for directories.

    According to the official docs written by Microsoft, it returns ENOACCES if the
    supplied filename is a directory. Looks like a trainee implemented the function.
    """
    if sys.platform == 'win32' and S_ISDIR(os.stat(dst)[ST_MODE]):
        if os.name == 'nt':
            st = os.stat(src)
            mode = S_IMODE(st[ST_MODE])
            if hasattr(os, 'chmod'):
                os.chmod(dst, mode) # KEEP THIS ONE!
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
        except (IOError, os.error), why:
            errors.append((srcname, dstname, why))
    if errors:
        raise EnvironmentError(str(errors))

# Code could come from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65203

# we currently do not support locking
LOCK_EX = LOCK_SH = LOCK_NB = 0

def lock(file, flags):
    raise NotImplementedError

def unlock(file):
    raise NotImplementedError

