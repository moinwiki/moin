# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend base classes.
"""

from __future__ import annotations

from typing import Any, Iterator
from typing_extensions import Self

from abc import abstractmethod, ABCMeta


class BackendBase(metaclass=ABCMeta):
    """
    Tie together a store for metadata and a store for data, read-only.
    """

    @property
    @abstractmethod
    def read_only(self) -> bool:
        """
        Indicates if the backend is read-only or not.
        """

    @classmethod
    @abstractmethod
    def from_uri(cls, uri: str) -> Self:
        """
        Create an instance using the data given in the URI.
        """

    @abstractmethod
    def create(self) -> None:
        """
        Create the backend.
        """

    @abstractmethod
    def destroy(self) -> None:
        """
        Destroy the backend; erase all meta/data it contains.
        """

    @abstractmethod
    def open(self) -> None:
        """
        Open the backend; allocate resources.
        """

    @abstractmethod
    def close(self) -> None:
        """
        Close the backend; free resources (except the stored meta/data!).
        """

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        Iterate over meta IDs.
        """

    @abstractmethod
    def retrieve(self, metaid: str) -> Any:
        """
        Return meta and data related to metaid.
        """

    @abstractmethod
    def store(self, meta, data) -> str:
        """
        Store meta and data into the backend; return the metaid.
        """

    @abstractmethod
    def remove(self, metaid: str, destroy_data: bool = False) -> None:
        """
        Delete meta and data related to metaid from the backend.
        """
