# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend base classes
"""


from __future__ import absolute_import, division

from abc import abstractmethod, ABCMeta


class BackendBase(object):
    """
    ties together a store for metadata and a store for data, readonly
    """
    __metaclass__ = ABCMeta

    @classmethod
    @abstractmethod
    def from_uri(cls, uri):
        """
        create an instance using the data given in uri
        """

    @abstractmethod
    def open(self):
        """
        open the backend, allocate resources
        """

    @abstractmethod
    def close(self):
        """
        close the backend, free resources (except the stored meta/data!)
        """

    @abstractmethod
    def __iter__(self):
        """
        iterate over metaids
        """

    @abstractmethod
    def retrieve(self, metaid):
        """
        return meta, data related to metaid
        """


class MutableBackendBase(BackendBase):
    """
    same as Backend, but read/write
    """
    @abstractmethod
    def create(self):
        """
        create the backend
        """

    @abstractmethod
    def destroy(self):
        """
        destroy the backend, erase all meta/data it contains
        """

    @abstractmethod
    def store(self, meta, data):
        """
        store meta, data into the backend, return the metaid
        """

    @abstractmethod
    def remove(self, metaid):
        """
        delete meta, data related to metaid from the backend
        """

