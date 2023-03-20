"""
Profile backend interface
"""
from typing import (
    Optional,
    Sequence,
)
from abc import abstractmethod
from softlab.shui import DatabaseBackend
from softlab.shui.profile.base import Profile

class ProfileBackend(DatabaseBackend):
    """
    Abstract definition of profile backend, derived from ``DatabaseBackend``

    Additional actions for user:
    - list_profiles -- list ID sequence of all profiles in backend
    - load_profile -- load a profile with given ID
    - save_profile -- save a profile to the backend
    - remove_profile -- remove a profile with the given ID

    Methods need be implemented by derived class:
    - connect_impl -- perform actual connection
    - disconnect_impl -- perform actual disconnection
    - list_impl -- list ID sequence of all profiles actually
    - load_impl -- load a profile with given ID actually
    - save_impl -- save a profile to the backend actually
    - remove_impl -- remove a profile from the backend actually
    """

    def __init__(self, type: str) -> None:
        super().__init__(type)

    def list_profiles(self) -> Sequence[str]:
        """List all IDs of profiles in the backend"""
        if self.connected:
            return self.list_impl()
        else:
            raise ConnectionError('The backend has not connected')

    def load_profile(self, id: str) -> Optional[Profile]:
        """Load a profile with the given ID"""
        if self.connected:
            return self.load_impl(id)
        else:
            raise ConnectionError('The backend has not connected')

    def save_profile(self, profile: Profile) -> bool:
        """Save a profile into the backend"""
        if self.connected:
            return self.save_impl(profile)
        else:
            raise ConnectionError('The backend has not connected')

    def remove_profile(self, id: str) -> None:
        """Remove a profile with the given ID"""
        if self.connected:
            self.remove_impl(id)
        else:
            raise ConnectionError('The backend has not connected')

    @abstractmethod
    def list_impl(self) -> Sequence[str]:
        """Actual listing of profile IDs, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def load_impl(self, id: str) -> Optional[Profile]:
        """Actual loading of a profile, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def save_impl(self, profile: Profile) -> bool:
        """Actual saving of a profile, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def remove_impl(self, id: str) -> None:
        """Actual removal of a profile, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')
