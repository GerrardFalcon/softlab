"""
Memory backend of profile
"""
from datetime import datetime
from typing import (
    Any,
    Optional,
    Sequence,
    Dict,
)
from triq.profile.backend.base import ProfileBackend
from triq.profile import Profile

_profiles: Dict[str, Profile] = {}

class MemoryProfileBackend(ProfileBackend):
    """Profile backend by using memory dictionary directly"""
    def __init__(self) -> None:
        super().__init__('memory')

    def connect_raw(self, _: Dict[str, Any]) -> bool:
        return True

    def disconnect_raw(self) -> bool:
        return True

    def list_raw(self) -> Sequence[str]:
        return list(_profiles.keys())

    def load_raw(self, id: str) -> Optional[Profile]:
        return _profiles.get(id, None)

    def save_raw(self, profile: Profile) -> bool:
        if isinstance(profile, Profile):
            _profiles[profile.profile_id] = profile
            return True
        else:
            return False

    def remove_raw(self, id: str) -> None:
        _profiles.pop(id, None)

if __name__ == '__main__':
    backend = MemoryProfileBackend()
    print(f'Create backend: {backend.snapshot()}')
    assert(backend.connect())
    assert(len(backend.list_profiles()) == 0)
    print('Save a profile via backend')
    assert(backend.save_profile(Profile(
        '0000', 'Test', 'Cat', datetime.now(), datetime.now(), True
    )))
    assert(len(backend.list_profiles()) == 1)
    backend2 = MemoryProfileBackend()
    backend2.connect()
    print(f'Create another backend: {backend2.snapshot()}')
    assert(backend.connected and backend2.connected)
    assert(backend.list_profiles() == backend2.list_profiles())
    ids = backend.list_profiles()
    print(f'Profile ID list: {ids}')
    assert(len(ids) == 1)
    assert(ids[0] == '0000')
    profile = backend2.load_profile(ids[0])
    assert(profile.owner_id == 'Cat')
    print(f'Load profile from second backend: {profile}')
