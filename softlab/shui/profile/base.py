"""
Data structure of profile
"""
from typing import (
    Any,
    Dict,
    Iterable,
    Tuple,
    List,
    Optional,
)
import re
from datetime import datetime
import logging
from softlab.jin import (
    ValType,
    ValInt,
    ValNumber,
    ValString,
    ValPattern,
    ValSequence,
)

_AVAILABLE_TYPES = [
    'string', 'int', 'float', 'bool',
]
"""Avaiable value types for profile item"""

_KEY_RE_PATTERN = r'^_*[A-Za-z]\w*(\._*[A-Za-z]\w*)*$'
"""Regular expression pattern for profile item key"""

_logger = logging.getLogger(__name__)

class ProfileItem:
    """
    Single profile item
    
    Arguments for creation:
    - profile_id -- ID of belonging profile
    - key -- item key, non empty, match the pattern [_KEY_RE_PATTERN]
    - value -- initial value
    - value_type -- type of value, one of [_AVAILABLE_TYPES]
    - is_list -- whether the item is a list
    - validator -- validation info, for 'int', 'float' and normal 'string',
                   only 'min' and 'max' are valid, for 'string' with specific
                   pattern, only 'pattern' is valid
    - is_valid -- whether the item is valid

    Properties:
    - profile_id -- ID of belonging profile, read-write
    - key -- item key, read-only
    - value -- item value, read-write
    - value_type -- type of value, read-only
    - is_list -- whether the item is a list, read-only
    - validator -- validation info, read-only
    - is_valid -- whether the item is valid, read-write
    """

    def __init__(self,
                 profile_id: str,
                 key: str, value: Any,
                 value_type: str = 'string', is_list: bool = False,
                 validator: Dict[str, Any] = {},
                 is_valid: bool = True) -> None:
        self._profile_id = profile_id # record profile ID
        key = str(key) # process key
        if re.match(_KEY_RE_PATTERN, key) is None:
            raise ValueError(f'Invalid key "{key}"')
        self._key = key
        value_type = str(value_type) # process value type
        if not value_type in _AVAILABLE_TYPES:
            raise ValueError(f'Invalid value type "{value_type}"')
        self._value_type = value_type
        self._is_list = bool(is_list)
        validator_keys = []
        if value_type == 'int':
            self._parser = int
            self._vals = ValInt(
                int(validator.get('min', -1000000000)),
                int(validator.get('max', 1000000000)),
            )
            validator_keys = ['min', 'max']
        elif value_type == 'float':
            self._parser = float
            self._vals = ValNumber(
                float(validator.get('min', '-inf')),
                float(validator.get('max', 'inf')),
            )
            validator_keys = ['min', 'max']
        elif value_type == 'bool':
            self._parser = bool
            self._vals = ValType(bool)
        else:
            self._parser = str
            if 'pattern' in validator:
                self._vals = ValPattern(str(validator['pattern']))
                validator_keys = ['pattern']
            else:
                self._vals = ValString(
                    int(validator.get('min', 0)),
                    int(validator.get('max', 1000000)),
                )
                validator_keys = ['min', 'max']
        if self._is_list:
            self._vals = ValSequence(self._vals)
        self._validator = {}
        for v_key in validator_keys:
            if v_key in validator:
                self._validator[v_key] = validator[v_key]
        self._value: Any = None # initialize value
        self.set(value)
        self._is_valid = bool(is_valid) # whether it is valid

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @profile_id.setter
    def profile_id(self, val: str) -> None:
        self._profile_id = str(val)

    @property
    def key(self) -> str:
        return self._key

    @property
    def value_type(self) -> str:
        return self._value_type

    @property
    def is_list(self) -> bool:
        return self._is_list

    @property
    def validator(self) -> Dict[str, Any]:
        return self._validator

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @is_valid.setter
    def is_valid(self, is_valid: bool) -> None:
        self._is_valid = bool(is_valid)

    def get(self) -> Any:
        return self._value

    def set(self, val: Any) -> None:
        try:
            if self.is_list:
                self._value = list(map(self._parser, val))
            else:
                self._value = self._parser(val)
            self._vals.validate(self._value)
        except Exception:
            _logger.critical(f'Failed to initialize value {val}, '
                             f'require {self.value_type}, '
                             f'validator {self._vals}')
            raise

    value = property(get, set, doc='item value')

    def copy(self) -> 'ProfileItem':
        return ProfileItem(
            self.profile_id, self.key, self.value,
            self.value_type, self.is_list, self.validator, self.is_valid)

    def __repr__(self) -> str:
        return f'{self.key}: {self.value}'

    def __call__(self, *args: Any) -> Any:
        """Get or set attribute value, makes attribute callable"""
        if len(args) == 0:
            return self.get() # get value
        else:
            self.set(args[0]) # set value

class Profile:
    """
    A profile is a dictionary of items with certain metainfo

    Arguments in creation:
    - profile_id -- ID of profile
    - name -- readable name
    - owner_id -- ID of owner
    - created_at -- when the profile was created
    - modified_at -- when the profile was last modified
    - is_valid -- whether the profile is valid

    Properties:
    - profile_id -- ID of profile, read-only
    - name -- readable name, read-write
    - owner_id -- ID of owner, read-only
    - created_at -- when the profile was created, read-only
    - modified_at -- when the profile was last modified, read-write
    - is_valid -- whether the profile is valid, read-write

    Ways to access items:
    - items() -- returns list of tuples of key and item
    - item(key) -- return item with the given key
    - iterate profile -- just like iterating the item dictionary
    """
    def __init__(self,
                 profile_id: str,
                 name: str, owner_id: str,
                 created_at: datetime, modified_at: datetime,
                 is_valid: bool = True) -> None:
        self._profile_id = str(profile_id)
        self._name = str(name)
        self._owner = str(owner_id)
        if not isinstance(created_at, datetime):
            raise TypeError(f'Invalid created time {type(created_at)}')
        self._created_at = created_at
        if not isinstance(modified_at, datetime):
            raise TypeError(f'Invalid modified time {type(modified_at)}')
        self._modified_at = modified_at
        if self.modified_at < self.created_at:
            raise ValueError(f'Modified time {modified_at} should be later '
                             f'than created time {created_at}')
        self._is_valid = bool(is_valid)
        self._items: Dict[str, ProfileItem] = {}

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, val: str) -> None:
        self._name = str(val)

    @property
    def owner_id(self) -> str:
        return self._owner

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def modified_at(self) -> datetime:
        return self._modified_at

    @modified_at.setter
    def modified_at(self, val: datetime) -> None:
        if not isinstance(val, datetime):
            raise TypeError(f'Invalid modified time {type(val)}')
        if val < self.created_at:
            raise ValueError(f'Modified time {val} should be later than '
                             f'created time {self.created_at}')
        self._modified_at = val

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @is_valid.setter
    def is_valid(self, is_valid: bool) -> None:
        self._is_valid = bool(is_valid)

    def items(self) -> List[Tuple[str, ProfileItem]]:
        """Get list of tuples of key and its corresponding item"""
        return list(map(
            lambda pair: (pair[0], pair[1].copy()),
            self._items.items(),
        ))

    def item(self, key: str) -> Optional[ProfileItem]:
        """Get item with the [key]"""
        return self._items.get(str(key), None)

    def insert_item(self, item: ProfileItem) -> None:
        """Add or update the given [item] into profile"""
        if isinstance(item, ProfileItem):
            item.profile_id = self.profile_id
            self._items[item.key] = item.copy()
        else:
            raise TypeError(f'Invalid profile item type {type(item)}')

    def clear(self, key: Optional[str] = None) -> None:
        """Clear item with given [key], clear all if [key] is None"""
        if key is None:
            self._items = {}
        else:
            key = str(key)
            if key in self._items:
                self._items.pop(key)

    def __len__(self):
        """Get count of itemes"""
        return len(self._items)

    def __iter__(self):
        """Start iteration of item dictionary"""
        return iter(self._items)

    def __repr__(self) -> str:
        return '{}: {}{}{}'.format(
            self.profile_id, '{',
            ', '.join(map(str, self._items.values())), '}',
        )

    def __call__(self, *args: Any) -> Optional[ProfileItem]:
        if len(args) > 0:
            return self.item(args[0])
        return None

if __name__ == '__main__':
    print('Test profile item')
    item = ProfileItem(
        '', 'qchip.qubit_count', 20,
        value_type='int',
        validator={'min': 1},
    )
    print(f'Create item: {item}')
    assert(item.profile_id == '')
    assert(item.key == 'qchip.qubit_count')
    assert(item.value == 20)
    assert(item.validator['min'] == 1)
    assert(item.value_type == 'int')
    properties = [
        'profile_id', 'key', 'value',
        'value_type', 'is_list', 'validator', 'is_valid']
    for p in properties:
        assert(hasattr(item, p))
        print(f'item\'s {p}: {getattr(item, p)}')
    print()

    print('Test profile')
    profile = Profile(
        '0101010101', 'Customized profile', 'cat',
        datetime.fromisoformat('2012-12-21'),
        datetime.fromisoformat('2021-11-11'),
    )
    print(f'Create profile: {profile}')
    assert(len(profile) == 0)
    profile.insert_item(item)
    for i in range(profile('qchip.qubit_count')()):
        profile.insert_item(ProfileItem(
            profile.profile_id, f'qchip.qubit{i}.measure_frequency',
            6.1233444e9 + i * 5.33437e7, value_type='float',
            validator={'min': 1e8, 'max': 100e9},
        ))
    assert(len(profile) == item() + 1)
    print(f'Iterate profile:')
    for key, item in profile.items():
        print(f'{key}: {item()}')
    assert(isinstance(profile, Iterable))
    keys = []
    for key in profile:
        keys.append(key)
    assert(len(keys) == len(profile))
    print(f'All item keys: {keys}')
