"""
Getter function of backend
"""
from typing import (
    Any,
    Optional,
    Dict,
)
from triq.profile.backend.base import ProfileBackend
from triq.profile.backend.memory import MemoryProfileBackend
from triq.profile.backend.json_profile import JsonProfileBackend
import logging

_logger = logging.getLogger(__name__) # prepare logger

def get_profile_backend(type: str, 
                        args: Optional[Dict[str, Any]] = None,
                        connect: bool = True) -> ProfileBackend:
    """
    Get profile backend

    Arguments:
    type -- backend type
    args -- connect arguments
    connect -- whether to connect at beginning

    Returns:
    the backend with the given type

    Throws:
    - If the given type is empty, raise a value error
    - If there is no backend implementation of the given type, raise a
      not-implemented error
    """
    backend_type = str(type)
    if len(backend_type) == 0:
        raise ValueError('Backend type is empty')
    if backend_type == 'memory':
        backend = MemoryProfileBackend()
    elif backend_type == 'json':
        backend = JsonProfileBackend()
    else:
        raise NotImplementedError(
            f'Backend of type {type} is not implemented')
    if connect:
        if not backend.connect(args):
            _logger.warning(f'Failed to connect: {backend.last_error}')
    return backend

def get_profile_backend_by_info(info: Dict[str, Any], 
                                connect: bool = True) -> ProfileBackend:
    """
    Get profile backend by using the given information

    Arguments:
    info -- backend information, 'type' key is necessary, and the optional
            key 'arguments' related to connect arguments
    connect -- whether to connect at beginning

    Returns:
    the backend with the given type

    Throws:
    - If the given info is not a dictionary, raise a type error
    """
    if not isinstance(info, Dict):
        raise TypeError(f'Type of info is invalid: {type(info)}')
    return get_profile_backend(
        info['type'], info.get('arguments', None), connect)

if __name__ == '__main__':
    import os
    backend = get_profile_backend('memory')
    assert(isinstance(backend, MemoryProfileBackend))
    print(f'Get backend with type: {backend.backend_type}')
    print(f'Status of backend: {backend.status}')
    print()

    json_name = 'profile.json'
    backend = get_profile_backend('json', {'path': json_name})
    assert(isinstance(backend, JsonProfileBackend))
    print(f'Get backend with type: {backend.backend_type}')
    print(f'Status of backend: {backend.status}')
    backend.disconnect()
    print(f'Read file {json_name}:')
    with open(json_name, 'r') as f:
        for line in f:
            print(line)
    os.remove(json_name)
    print()

    try:
        backend = get_profile_backend('asdg')
    except NotImplementedError:
        print('No implementation for type "asdg"')
