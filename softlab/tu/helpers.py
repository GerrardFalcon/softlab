"""Helper elements"""

from typing import (
    Any,
    List,
    Dict,
)

class Delegated:
    """
    Mixin class to create attributes of this object by
    delegating them to one or more dictionaries and/or objects.

    Inspired by ``qcodes.utils.helpers.DelegateAttributes``.
    """

    __delegate_attr_dicts = set()
    """
    A list of names (strings) of dictionaries
    which are (or will be) attributes of ``self``, whose keys should
    be treated as attributes of ``self``.
    """
    __delegate_attr_objects = set()
    """
    A list of names (strings) of objects
    which are (or will be) attributes of ``self``, whose attributes
    should be passed through to ``self``.
    """
    __omit_delegate_attrs = set()
    """
    A list of attribute names (strings)
    to *not* delegate to any other dictionary or object.
    """

    def __getattr__(self, key: str) -> Any:
        if key in self.__omit_delegate_attrs:
            raise AttributeError(
                f'{type(self)} does not delegate attribute {key}')

        for name in self.__delegate_attr_dicts:
            if key == name: # needed to prevent infinite loops!
                raise AttributeError(
                    f'{key} has not been created in {type(self)}')
            try:
                d = getattr(self, name, None)
                if d is not None:
                    return d[key]
            except KeyError:
                pass

        for name in self.__delegate_attr_objects:
            if key == name:
                raise AttributeError(
                    f'{key} has not been created in {type(self)}')
            try:
                obj = getattr(self, name, None)
                if obj is not None:
                    return getattr(obj, key)
            except AttributeError:
                pass

        raise AttributeError(
            f'{type(self)} does not delegate attribute {key}')

    def __dir__(self) -> List[str]:
        names = list(super().__dir__())
        for name in self.__delegate_attr_dicts:
            d = getattr(self, name, None)
            if isinstance(d, Dict):
                names += [k for k in d.keys()
                          if k not in self.__omit_delegate_attrs]

        for name in self.__delegate_attr_objects:
            obj = getattr(self, name, None)
            if obj is not None:
                names += [k for k in dir(obj)
                          if k not in self.__omit_delegate_attrs]

        return sorted(set(names))
    
    def add_delegate_attr_dict(self, name: str) -> None:
        """Add name of delegated attribute dict"""
        if not isinstance(name, str) or len(name) == 0:
            raise ValueError('Invalid delegate attribute dict name')
        self.__delegate_attr_dicts.add(name)
    
    def add_delegate_attr_objects(self, name: str) -> None:
        """Add name of delegated attribute object"""
        if not isinstance(name, str) or len(name) == 0:
            raise ValueError('Invalid delegate object dict name')
        self.__delegate_attr_dicts.add(name)

    def add_omit_delegate_attrs(self, name: str) -> None:
        """Add name of omitting delegate attribute key"""
        if not isinstance(name, str) or len(name) == 0:
            raise ValueError('Invalid omitting delegate attribute key')
        self.__omit_delegate_attrs.add(name)
