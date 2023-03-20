"""
Management of profile
"""
from typing import (
    Any,
    Dict,
    Optional,
    Sequence,
)
import logging
from datetime import datetime
import uuid
from triq.database import DatabaseBackend
from triq.profile.base import Profile
from triq.profile.backend import (
    ProfileBackend,
    get_profile_backend,
)

_logger = logging.getLogger(__name__)

class ProfileInfo:
    """
    Information of a profile
    
    Properties:
    - profile_id -- ID of profile
    - name -- readable name
    - owner_id -- ID of owner
    - created_at -- when the profile was created
    - modified_at -- when the profile was last modified
    - is_valid -- whether the profile is valid
    """

    def __init__(
        self, id: str,
        name: str,
        owner_id: str,
        created_at: datetime,
        modified_at: datetime,
        is_valid: bool,
    ) -> None:
        if isinstance(id, str) and isinstance(name, str) \
                and isinstance(owner_id, str) \
                and isinstance(created_at, datetime) \
                and isinstance(modified_at, datetime) \
                and isinstance(is_valid, bool):
            self.profile_id = id
            self.name = name
            self.owner_id = owner_id
            self.created_at = created_at
            self.modified_at = modified_at
            self.is_valid = is_valid
        else:
            raise TypeError(
                f'Invalid input type: id {type(id)}, name {type(name)}, '
                f'owner_id {type(owner_id)}, created_at {type(created_at)}, '
                f'modified_at {type(modified_at)}, is_valid {type(is_valid)}'
            )

    @staticmethod
    def from_profile(profile: Profile) -> 'ProfileInfo':
        if isinstance(profile, Profile):
            return ProfileInfo(
                profile.profile_id, profile.name, profile.owner_id,
                profile.created_at, profile.modified_at, profile.is_valid,
            )

class ProfileManage:
    """Management of profiles"""

    def __init__(self) -> None:
        self._profiles: Dict[str, Optional[Profile]] = {}
        self._arguments: Dict[str, Any] = {}
        self._backend: Optional[ProfileBackend] = None

    @property
    def status(self) -> DatabaseBackend.Status:
        """Backend status"""
        if isinstance(self._backend, ProfileBackend):
            return self._backend.status
        else:
            return DatabaseBackend.Status.NotConnected

    def set_backend(self, type: str, arguments: Dict[str, Any] = {}) -> bool:
        """Set and connect to backend, refresh profile list if succeed"""
        try:
            backend = get_profile_backend(type, arguments)
        except Exception:
            _logger.critical(f'Failed get backend {type} with {arguments}')
            return False
        self._backend = backend
        self._arguments = arguments
        self._profiles = {}
        try:
            for id in backend.list_profiles():
                self._profiles[id] = None
        except Exception:
            _logger.warn(
                f'Failed to get profile list in backend {backend.snapshot()}')
        self._check_last_error()
        return True

    def disconnect(self) -> None:
        """Disconnect from backend"""
        if isinstance(self._backend, ProfileBackend):
            self._backend.disconnect()

    def reconnect(self) -> bool:
        """Reconnect to backend"""
        if isinstance(self._backend, ProfileBackend):
            self._backend.disconnect()
            return self._backend.connect(self._arguments)
        else:
            return False

    def refresh_list(self) -> bool:
        """Refresh profile list"""
        if not isinstance(self._backend, ProfileBackend):
            _logger.warn('Backend is invalid')
            return False
        if not self._backend.connected:
            if not self._backend.connect(self._arguments):
                _logger.warn('Failed to connect backend')
                self._check_last_error()
                return False
        rst = True
        try:
            profiles = {}
            for id in self._backend.list_profiles():
                if id in self._profiles:
                    profiles[id] = self._profiles[id]
                else:
                    profiles[id] = None
                self._profiles = profiles
        except Exception as e:
            _logger.critical(f'Exception in refresh: {e}')
            rst = False
        self._check_last_error()
        return rst

    def get_list(self) -> Sequence[str]:
        """Get list of profile IDs"""
        return self._profiles.keys()

    def get_profile(self, id: str) -> Optional[Profile]:
        """Get profile with given ID"""
        return self._profiles.get(id, None)

    def get_info_list(self) -> Sequence[ProfileInfo]:
        """Get list of all profile info"""
        infos = []
        for id in self._profiles:
            if not isinstance(self._profiles[id], Profile):
                try:
                    self._profiles[id] = self._backend.load_profile(id)
                except Exception as e:
                    _logger.warn(f'Exception in loading {id}: {e}')
                    self._profiles[id] = None
            if isinstance(self._profiles[id], Profile):
                infos.append(ProfileInfo.from_profile(self._profiles[id]))
        return infos

    def create_profile(self, name: str, owner_id: str) -> Optional[Profile]:
        """Create a new profile with given name and owner"""
        if not isinstance(self._backend, ProfileBackend):
            _logger.warn(f'No valid backend to create profile')
            return None
        if not self._backend.connected:
            self._backend.connect(self._arguments)
        if not self._backend.connected:
            _logger.warn(
                f'Failed to connect backend: {self._backend.last_error}')
            return None
        profile: Optional[Profile] = Profile(
            str(uuid.uuid4()), name, owner_id,
            datetime.now(), datetime.now(), True,
        )
        if self._backend.save_profile(profile):
            self._profiles[profile.profile_id] = profile
        else:
            _logger.warn(f'Failed to save {profile.profile_id} to backend')
            profile = None
        self._check_last_error()
        return profile

    def update_profile(self, profile: Profile) -> bool:
        """Update profile into the management and its backend"""
        if not isinstance(profile, Profile):
            raise TypeError(f'Invalid profile type {type(profile)}')
        if not isinstance(self._backend, ProfileBackend):
            _logger.warn('No valid backend to update profile')
            return False
        if not self._backend.connected:
            self._backend.connect(self._arguments)
        if not self._backend.connected:
            _logger.warn(
                f'Failed to connect backend: {self._backend.last_error}')
            return False
        rst = True
        if self._backend.save_profile(profile):
            self._profiles[profile.profile_id] = profile
        else:
            _logger.warn(f'Failed to save {profile.profile_id} to backend')
            rst = False
        self._check_last_error()
        return rst

    def remove_profile(self, id: str) -> None:
        """Remove a profile with given ID"""
        id = str(id)
        if len(id) == 0:
            raise ValueError('Default profile cannot be removed')
        if not isinstance(self._backend, ProfileBackend):
            raise RuntimeError('No valid backend to update profile')
        if not self._backend.connected:
            self._backend.connect(self._arguments)
        if not self._backend.connected:
            raise RuntimeError(
                f'Failed to connect backend: {self._backend.last_error}')
        try:
            self._backend.remove_profile(id)
            self._profiles.pop(id, None)
        except Exception:
            self._check_last_error()
            raise

    def _check_last_error(self):
        if isinstance(self._backend, ProfileBackend):
            error = self._backend.last_error
            if len(error) > 0:
                _logger.warn(f'Error in backend: {error}')
            self._backend.clear_errors()
