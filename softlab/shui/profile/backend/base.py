"""
Profile backend interface
"""
from typing import (
    Optional,
    Sequence,
)
from abc import abstractmethod
from softlab.shui import DatabaseBackend
from softlab.shui.profile import Profile

class ProfileBackend(DatabaseBackend):
    """
    Abstract definition of profile backend, derived from ``DatabaseBackend``

    Additional actions for user:
    - list_profiles -- list ID sequence of all profiles in backend
    - load_profile -- load a profile with given ID
    - save_profile -- save a profile to the backend
    - remove_profile -- remove a profile with the given ID

    Methods need be implemented by derived class:
    - connect_raw -- perform actual connection
    - disconnect_raw -- perform actual disconnection
    - list_raw -- list ID sequence of all profiles actually
    - load_raw -- load a profile with given ID actually
    - save_raw -- save a profile to the backend actually
    - remove_raw -- remove a profile from the backend actually
    """

    def __init__(self, type: str) -> None:
        super().__init__(type)

    def list_profiles(self) -> Sequence[str]:
        """List all IDs of profiles in the backend"""
        if self.connected:
            return self.list_raw()
        else:
            raise ConnectionError('The backend has not connected')

    def load_profile(self, id: str) -> Optional[Profile]:
        """Load a profile with the given ID"""
        if self.connected:
            return self.load_raw(id)
        else:
            raise ConnectionError('The backend has not connected')

    def save_profile(self, profile: Profile) -> bool:
        """Save a profile into the backend"""
        if self.connected:
            return self.save_raw(profile)
        else:
            raise ConnectionError('The backend has not connected')

    def remove_profile(self, id: str) -> None:
        """Remove a profile with the given ID"""
        if self.connected:
            self.remove_raw(id)
        else:
            raise ConnectionError('The backend has not connected')

    @abstractmethod
    def list_raw(self) -> Sequence[str]:
        """Actual listing of profile IDs, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def load_raw(self, id: str) -> Optional[Profile]:
        """Actual loading of a profile, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def save_raw(self, profile: Profile) -> bool:
        """Actual saving of a profile, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def remove_raw(self, id: str) -> None:
        """Actual removal of a profile, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')
