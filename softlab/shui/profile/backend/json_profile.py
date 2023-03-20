"""
Json backend of profile
"""
from typing import (
    Any,
    Optional,
    Sequence,
    Dict,
)
import os
import logging
import json
from datetime import datetime
from triq.profile.backend.base import ProfileBackend
from triq.profile import Profile
from triq.profile.base import ProfileItem

_logger = logging.getLogger(__name__)

def _add_item(profile: Profile, raw_item: Dict[str, Any]) -> None:
    key = str(raw_item.get('key', ''))
    if len(key) > 0:
        profile.insert_item(ProfileItem(
            profile.profile_id, key,
            raw_item['value'],
            str(raw_item['value_type']),
            bool(raw_item.get('is_list', False)),
            raw_item.get('validator', {}),
            bool(raw_item.get('is_valid', True)),
        ))

def _parse_profile(raw_profile: Dict[str, Any]) -> Profile:
    profile = Profile(
        str(raw_profile['profile_id']),
        str(raw_profile.get('name', '')),
        str(raw_profile.get('owner_id', '')),
        datetime.fromisoformat(raw_profile['created_at']),
        datetime.fromisoformat(raw_profile['modified_at']),
        bool(raw_profile.get('is_valid', True)),
    )
    for raw_item in raw_profile.get('items', []):
        _add_item(profile, raw_item)
    return profile

def _dump_item(item: ProfileItem) -> Dict[str, Any]:
    return {
        'key': item.key,
        'value': item.value,
        'value_type': item.value_type,
        'is_list': item.is_list,
        'validator': item.validator,
        'is_valid': item.is_valid,
    }

def _dump_profile(profile: Profile) -> Dict[str, Any]:
    return {
        'profile_id': profile.profile_id,
        'name': profile.name,
        'owner_id': profile.owner_id,
        'created_at': profile.created_at.isoformat(),
        'modified_at': profile.modified_at.isoformat(),
        'is_valid': profile.is_valid,
        'items': list(map(lambda key: _dump_item(profile.item(key)), profile))
    }

class JsonProfileBackend(ProfileBackend):
    def __init__(self) -> None:
        super().__init__('json')
        self._path: str = ''
        self._profiles: Dict[str, Profile] = {}

    def connect_raw(self, args: Dict[str, Any]) -> bool:
        self._profiles = {} # clear
        self._path = str(args.get('path', ''))
        if len(self._path) == 0:
            _logger.warn(f'No file name is given in {args}')
            return False
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r', encoding ='utf8') as f:
                    raw_profiles = json.load(f) # load data from file
                for raw_profile in raw_profiles:
                    profile = _parse_profile(raw_profile)
                    self._profiles[profile.profile_id] = profile
            except Exception as e:
                _logger.warn(f'Failed to load profiles from "{self._path}": {e}')
                return False
        else:
            try:
                with open(self._path, 'w', encoding ='utf8') as f:
                    json.dump([], f)
            except Exception as e:
                _logger.warn(f'Failed to create file "{self._path}": {e}')
                return False
        return True

    def disconnect_raw(self) -> bool:
        self._persistance()
        self._profiles = {}
        return True

    def list_raw(self) -> Sequence[str]:
        return list(self._profiles.keys())

    def load_raw(self, id: str) -> Optional[Profile]:
        return self._profiles.get(id, None)

    def save_raw(self, profile: Profile) -> bool:
        if isinstance(profile, Profile):
            self._profiles[profile.profile_id] = profile
            self._persistance()
            return True
        else:
            return False

    def remove_raw(self, id: str) -> None:
        if self._profiles.pop(id, None) is not None:
            self._persistance()

    def _persistance(self) -> None:
        if len(self._path) > 0:
            raw_profiles = list(map(
                lambda id: _dump_profile(self._profiles[id]), self._profiles
            ))
            try:
                with open(self._path, 'w', encoding ='utf8') as f:
                    json.dump(raw_profiles, f, ensure_ascii=False, indent=2)
                    f.flush()
            except Exception as e:
                _logger.warn(f'Failed to save profile to {self._path}: {e}')

if __name__ == '__main__':
    backend = JsonProfileBackend()
    print(f'Create backend: {backend.snapshot()}')
    assert(backend.connect({'path':'profile.json'}))
    assert(len(backend.list_profiles()) == 0)
    print('Save a profile via backend')
    profile = Profile(
        '0000', 'Test', 'Cat', datetime.now(), datetime.now(), True
    )
    profile.insert_item(ProfileItem(
        profile.profile_id, 'qubit_count', 20, 'int',
        validator={'min': 0},
    ))
    profile.insert_item(ProfileItem(
        profile.profile_id, 'vendor', 'petit-kayak'
    ))
    assert(backend.save_profile(profile))
    assert(len(backend.list_profiles()) == 1)
    backend2 = JsonProfileBackend()
    backend2.connect({'path':'profile.json'})
    print(f'Create another backend: {backend2.snapshot()}')
    assert(backend.connected and backend2.connected)
    assert(backend.list_profiles() == backend2.list_profiles())
    ids = backend.list_profiles()
    print(f'Profile ID list: {ids}')
    assert(len(ids) == 1)
    assert(ids[0] == profile.profile_id)
    profile2 = backend2.load_profile(ids[0])
    assert(profile2.owner_id == profile.owner_id)
    print(f'Load profile from second backend: {profile2}')
    os.remove('profile.json')
