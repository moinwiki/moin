# Copyright: Yusuke Shinyama (author)
# Copyright: Johannes Berg (coding style fixes and tcdb removal)
# License: Public Domain

"""
pycdb.py - Python implementation of cdb
"""


import os
from struct import pack, unpack
from array import array


def cdbhash(s, n=0L):
    """calc hash value with a given key"""
    return reduce(lambda h, c: ((h * 33) ^ ord(c)) & 0xffffffffL, s, n + 5381L)

if pack('=i', 1) == pack('>i', 1):
    def decode(x):
        a = array('I', x)
        a.byteswap()
        return a
    def encode(a):
        a.byteswap()
        return a.tostring()
else:
    def decode(x):
        a = array('I', x)
        return a
    def encode(a):
        return a.tostring()


def cdbiter(fp, eod):
    kloc = 2048
    while kloc < eod:
        fp.seek(kloc)
        (klen, vlen) = unpack('<II', fp.read(8))
        k = fp.read(klen)
        v = fp.read(vlen)
        kloc += 8 + klen + vlen
        yield (k, v)
    fp.close()


class CDBReader:
    def __init__(self, cdbname, docache=1):
        self.name = cdbname
        self._fp = file(cdbname, 'rb')
        hash0 = decode(self._fp.read(2048))
        self._hash0 = [(hash0[i], hash0[i+1]) for i in xrange(0, 512, 2)]
        self._hash1 = [None ] * 256
        self._eod = hash0[0]
        self._docache = docache
        self._cache = {}
        self._keyiter = None
        self._eachiter = None

    def __getstate__(self):
        raise TypeError

    def __setstate__(self, dict):
        raise TypeError

    def __getitem__(self, k):
        k = str(k)
        if k in self._cache:
            return self._cache[k]
        h = cdbhash(k)
        h1 = h & 0xff
        (pos_bucket, ncells) = self._hash0[h1]
        if ncells == 0:
            raise KeyError(k)
        hs = self._hash1[h1]
        if hs is None:
            self._fp.seek(pos_bucket)
            hs = decode(self._fp.read(ncells * 8))
            self._hash1[h1] = hs
        i = ((h >> 8) % ncells) * 2
        n = ncells * 2
        for _ in xrange(ncells):
            p1 = hs[i + 1]
            if p1 == 0: raise KeyError(k)
            if hs[i] == h:
                self._fp.seek(p1)
                (klen, vlen) = unpack('<II', self._fp.read(8))
                k1 = self._fp.read(klen)
                if k1 == k:
                    v1 = self._fp.read(vlen)
                    if self._docache:
                        self._cache[k] = v1
                    return v1
            i = (i + 2) % n
        raise KeyError(k)

    def get(self, k, failed=None):
        try:
            return self.__getitem__(k)
        except KeyError:
            return failed

    def has_key(self, k):
        try:
            self.__getitem__(k)
            return True
        except KeyError:
            return False

    def __contains__(self, k):
        return self.has_key(k)

    def firstkey(self):
        self._keyiter = None
        return self.nextkey()

    def nextkey(self):
        if not self._keyiter:
            self._keyiter = (k for (k, v) in cdbiter(self._fp, self._eod))
        try:
            return self._keyiter.next()
        except StopIteration:
            return None

    def each(self):
        if not self._eachiter:
            self._eachiter = cdbiter(self._fp, self._eod)
        try:
            return self._eachiter.next()
        except StopIteration:
            return None

    def iterkeys(self):
        return (k for (k, v) in cdbiter(self._fp, self._eod))

    def itervalues(self):
        return (v for (k, v) in cdbiter(self._fp, self._eod))

    def iteritems(self):
        return cdbiter(self._fp, self._eod)


class CDBMaker:
    def __init__(self, cdbname, tmpname):
        self.fn = cdbname
        self.fntmp = tmpname
        self.numentries = 0
        self._fp = file(tmpname, 'wb')
        self._pos = 2048
        self._bucket = [array('I') for _ in xrange(256)]

    def __len__(self):
        return self.numentries

    def __getstate__(self):
        raise TypeError

    def __setstate__(self, dict):
        raise TypeError

    def add(self, k, v):
        (k, v) = (str(k), str(v))
        (klen, vlen) = (len(k), len(v))
        self._fp.seek(self._pos)
        self._fp.write(pack('<II', klen, vlen))
        self._fp.write(k)
        self._fp.write(v)
        h = cdbhash(k)
        b = self._bucket[h % 256]
        b.append(h)
        b.append(self._pos)
        # sizeof(keylen)+sizeof(datalen)+sizeof(key)+sizeof(data)
        self._pos += 8 + klen + vlen
        self.numentries += 1
        return self

    def finish(self):
        self._fp.seek(self._pos)
        pos_hash = self._pos
        # write hashes
        for b1 in self._bucket:
            if not b1: continue
            blen = len(b1)
            a = array('I', [0] * blen * 2)
            for j in xrange(0, blen, 2):
                (h, p) = (b1[j], b1[j+1])
                i = ((h >> 8) % blen) * 2
                while a[i + 1]:
                    i = (i + 2) % len(a)
                a[i] = h
                a[i + 1] = p
            self._fp.write(encode(a))
        # write header
        self._fp.seek(0)
        a = array('I')
        for b1 in self._bucket:
            a.append(pos_hash)
            a.append(len(b1))
            pos_hash += len(b1) * 8
        self._fp.write(encode(a))
        self._fp.close()
        os.rename(self.fntmp, self.fn)

cdbmake = CDBMaker
init = CDBReader
