# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend base classes.
"""

from abc import abstractmethod, ABCMeta


class BackendBase(metaclass=ABCMeta):
    """
    Tie together a store for metadata and a store for data, read-only.
    """

    @classmethod
    @abstractmethod
    def from_uri(cls, uri):
        """
        Create an instance using the data given in the URI.
        """

    @abstractmethod
    def open(self):
        """
        Open the backend; allocate resources.
        """

    @abstractmethod
    def close(self):
        """
        Close the backend; free resources (except the stored meta/data!).
        """

    @abstractmethod
    def __iter__(self):
        """
        Iterate over meta IDs.
        """

    @abstractmethod
    def retrieve(self, metaid):
        """
        Return meta and data related to metaid.
        """


class MutableBackendBase(BackendBase):
    """
    Same as Backend, but read/write.
    """

    @abstractmethod
    def create(self):
        """
        Create the backend.
        """

    @abstractmethod
    def destroy(self):
        """
        Destroy the backend; erase all meta/data it contains.
        """

    @abstractmethod
    def store(self, meta, data):
        """
        Store meta and data into the backend; return the metaid.
        """

    @abstractmethod
    def remove(self, metaid, destroy_data=False):
        """
        Delete meta and data related to metaid from the backend.
        """
