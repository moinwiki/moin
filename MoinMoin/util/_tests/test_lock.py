# Copyright: 2005 by Florian Festi
# Copyright: 2007 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.module_tested Tests
"""


import tempfile, os, time, shutil

import pytest

from MoinMoin.util.lock import ExclusiveLock, WriteLock, ReadLock


class TestExclusiveLock(object):

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'lock_')
        self.test_dir_mtime_goal = time.time()
        self.test_dir_mtime_reported = os.stat(self.test_dir).st_mtime
        self.lock_dir = os.path.join(self.test_dir, "lock")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)

    def testBrokenTimeAPI(self):
        """ util.lock: os.stat().mtime consistency with time.time()

            the timestamp os.stat reports as st_mtime on a fresh file should
            be the same (or at least almost the same) as the time time.time()
            reported at this time.
            Differences of n*3600s are usually operating system bugs / limitations,
            Win32 (as of Win XP SP2 + hotfixes 2006-04-30) is broken if you set
            TZ to a different value than the rest of the system uses.
            E.g. if you set "TZ=GMT1EDT" (and the rest of the system is setup
            on german/berlin timezone), it will report 7200s difference in the
            summer.
        """
        diff = self.test_dir_mtime_reported - self.test_dir_mtime_goal # diff should be 0 or near 0
        assert abs(diff) <= 2

    def testTimeout(self):
        """ util.lock: ExclusiveLock: raise ValueError for timeout < 2.0 """
        pytest.raises(ValueError, ExclusiveLock, self.lock_dir, timeout=1.0)

    def testAcquire(self):
        """ util.lock: ExclusiveLock: acquire """
        lock = ExclusiveLock(self.lock_dir)
        assert lock.acquire(0.1)

    def testRelease(self):
        """ util.lock: ExclusiveLock: release

        After releasing a lock, new one could be acquired.
        """
        lock = ExclusiveLock(self.lock_dir)
        if not lock.acquire(0.1):
            pytest.skip("can't acquire lock")
        lock.release()
        assert lock.acquire(0.1)

    def testIsLocked(self):
        """ util.lock: ExclusiveLock: isLocked """
        lock = ExclusiveLock(self.lock_dir)
        if not lock.acquire(0.1):
            pytest.skip("can't acquire lock")
        assert lock.isLocked()
        lock.release()
        assert not lock.isLocked()

    def testExists(self):
        """ util.lock: ExclusiveLock: exists """
        lock = ExclusiveLock(self.lock_dir)
        if not lock.acquire(0.1):
            pytest.skip("can't acquire lock")
        assert lock.exists()

    def testIsExpired(self):
        """ util.lock: ExclusiveLock: isExpired """
        timeout = 2.0
        lock = ExclusiveLock(self.lock_dir, timeout=timeout)
        if not lock.acquire(0.1):
            pytest.skip("can't acquire lock")
        assert not lock.isExpired()
        time.sleep(timeout)
        assert lock.isExpired()

    def testExpire(self):
        """ util.lock: ExclusiveLock: expire """
        timeout = 2.0
        lock = ExclusiveLock(self.lock_dir, timeout=timeout)
        if not lock.acquire(0.1):
            pytest.skip("can't acquire lock")
        assert not lock.expire()
        time.sleep(timeout)
        assert lock.expire()

    def testExclusive(self):
        """ util.lock: ExclusiveLock: lock is exclusive """
        first = ExclusiveLock(self.lock_dir)
        second = ExclusiveLock(self.lock_dir)
        if not first.acquire(0.1):
            pytest.skip("can't acquire lock")
        assert not second.acquire(0.1)

    def testAcquireAfterTimeout(self):
        """ util.lock: ExclusiveLock: acquire after timeout

        Lock with one lock, try to acquire another after timeout.
        """
        timeout = 3.0 # minimal timeout is 2.0
        first = ExclusiveLock(self.lock_dir, timeout)
        second = ExclusiveLock(self.lock_dir, timeout)
        if not first.acquire(0.1):
            pytest.skip("can't acquire lock")
        if second.acquire(0.1):
            pytest.skip("first lock is not exclusive")
        # Second lock should be acquired after timeout
        assert second.acquire(timeout + 0.2)

    def unlock(self, lock, delay):
        time.sleep(delay)
        lock.release()

class TestWriteLock(object):
    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'lock_')
        self.lock_dir = os.path.join(self.test_dir, "writelock")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
    
    def test_writelock_acquire(self):
        """ util.lock: WriteLock: acquire """
        lock = WriteLock(self.lock_dir)
        assert lock.acquire(0.1)
        with pytest.raises(RuntimeError):
            assert lock.acquire(0.1)

    def test_haveReadLocks(self):
        """check if there is a ReadLock """
        timeout = 2.0 
        write_lock = WriteLock(self.lock_dir, timeout)
        read_lock = ReadLock(self.lock_dir)
        # acquired ReadLock
        read_lock.acquire(0.1)
        result_before = write_lock._haveReadLocks()
        assert result_before
        # try to acquire WriteLock
        write_lock.acquire()
        result_after = write_lock._haveReadLocks()
        assert result_after == False

class TestReadLock(object):
    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'lock_')
        self.lock_dir = os.path.join(self.test_dir, "readlock")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
    
    def test_readlock_acquire(self):
        """ util.lock: ReadLock: acquire """
        lock = ReadLock(self.lock_dir)
        assert lock.acquire(0.1)
        with pytest.raises(RuntimeError):
            assert lock.acquire(0.1)

coverage_modules = ['MoinMoin.util.lock']

