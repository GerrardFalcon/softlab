"""Drivers for VISA-based devices"""

from typing import (
    Any,
    Optional,
    Callable,
)
from softlab.tu.parameter import Parameter
import pyvisa as visa
import logging

_logger = logging.getLogger(__name__)

class VisaHandle():
    """
    Simple handle of VISA connection
    
    Properties:
    - address --- address of visa device, read-only
    - timeout --- time-out time, unit: seconds
    - read_termination --- termination in reading
    - write_termination --- termination in writing
    
    Public Methods:
    - open --- open device
    - close --- close device
    - clear --- clear visa buffer
    - read --- read as string
    - read_raw --- read as raw bytes
    - write --- write as string
    - write_raw --- write as raw bytes
    - query --- query as string
    """

    def __init__(self,
                 address: str, visalib: Optional[str] = None,
                 timeout: Optional[float] = 5.0,
                 read_termination: Optional[str] = '\n',
                 write_termination: Optional[str] = '\n',
                 device_clear: bool = True) -> None:
        """
        Initialization

        Args:
        - address --- address of visa device
        - visalib --- specified visa lib, use default (ni) if None
        - timeout --- time-out time, unit: seconds
        - read_termination --- termination in reading
        - write_termination --- termination in writing
        - device_clear --- whether to clear device buffer
        """
        self._backend: str = ''
        self._lib = visalib if isinstance(visalib, str) else None
        self._resource: Optional[visa.resources.MessageBasedResource] = None

        address = str(address)
        if len(address) > 0 and '@' in address:
            address, lib_in_addr = address.split('@')
            if self._lib is None:
                self._lib = '@' + lib_in_addr

        try:
            if self._lib:
                _logger.info(f'Opening PyVISA resource with {self._lib}')
                resource_manager = visa.ResourceManager(self._lib)
                self._backend = self._lib.split('@')[1]
            else:
                _logger.info('Opening PyVISA resource with default backend')
                resource_manager = visa.ResourceManager()
                self._backend = 'ni'
            _logger.info(f'Opening PyVISA resource at {address}')
            resource = resource_manager.open_resource(address)
            if not isinstance(resource, visa.resources.MessageBasedResource):
                resource.close()
                raise TypeError(
                    f'{__class__} only support MessageBasedResource '
                    f'instead of {type(resource)}')
            self._resource = resource
            self._address = address
        except Exception as e:
            _logger.info(f'Failed to connect {address}')
            raise e

        if device_clear:
            self.clear()

        self.timeout = timeout
        self.read_termination = read_termination
        self.write_termination = write_termination

    @property
    def address(self) -> str:
        """Get device address"""
        return self._address

    @property
    def timeout(self) -> Optional[float]:
        """Get timeout in seconds"""
        if self._resource:
            return self._resource.timeout
        return None
    
    @timeout.setter
    def timeout(self, timeout: Optional[float]) -> None:
        """Set timeout in seconds"""
        if self._resource:
            self._resource.timeout = timeout

    @property
    def read_termination(self) -> Optional[str]:
        """Get reading termination"""
        if self._resource:
            return self._resource.read_termination
    
    @read_termination.setter
    def read_termination(self, termination: Optional[str]) -> None:
        """Set reading termination"""
        if self._resource:
            self._resource.read_termination = termination

    @property
    def write_termination(self) -> Optional[str]:
        """Get writing termination"""
        if self._resource:
            return self._resource.write_termination
    
    @write_termination.setter
    def write_termination(self, termination: Optional[str]) -> None:
        """Set writing termination"""
        if self._resource:
            self._resource.write_termination = termination

    def open(self) -> None:
        """Open device"""
        if self._resource:
            self._resource.open()

    def clear(self) -> None:
        """Clear buffer"""
        if self._resource:
            self._resource.clear()

    def close(self) -> None:
        """Close device"""
        if self._resource:
            self._resource.close()

    def read(self, encoding: Optional[str] = None) -> str:
        """Read as string"""
        if self._resource:
            return self._resource.read(encoding=encoding)
        raise RuntimeError('Invalid visa resource')
        
    def read_raw(self, size: Optional[int] = None) -> bytes:
        """Read as raw bytes"""
        if self._resource:
            return self._resource.read_raw(size=size)
        raise RuntimeError('Invalid visa resource')
    
    def write(self, message: str, encoding: Optional[str] = None) -> int:
        """Write as string"""
        if self._resource:
            return self._resource.write(message=message, encoding=encoding)
        raise RuntimeError('Invalid visa resource')
    
    def write_raw(self, message: bytes) -> int:
        """Write as raw bytes"""
        if self._resource:
            return self._resource.write(message=message)
        raise RuntimeError('Invalid visa resource')
    
    def query(self, command: str, delay: Optional[float] = None) -> str:
        """Query as string"""
        if self._resource:
            return self._resource.query(command, delay)
        raise RuntimeError('Invalid visa resource')
    
class VisaParameter(Parameter):
    """
    Simple parameter in visa device, the value can be set and/or get by
    using simple commands
    """

    def __init__(self, name: str, handle: VisaHandle,
                 get_cmd: str = '', set_cmd: str = '',
                 get_parser: Optional[Callable] = None,
                 set_parser: Optional[Callable] = None,
                 read_after_setting: bool = False,
                 encoding: Optional[str] = None,
                 query_delay: Optional[float] = None,
                 **kwargs) -> None:
        """
        Initialization

        Args:
        - name --- parameter name
        - handle --- visa device handle
        - get_cmd --- command to get value, use buffered value if empty
        - set_cmd --- command to set value, no actual setting if empty
        - get_parser --- function to parse got string into meaningful value
        - set_parser --- function to parse value to device readable string
        - read_after_setting --- whether to perform a reading after setting
        - encoding --- encoding in read and write operations, optional
        - query_delay --- delay when querying value from device 
        """
        super().__init__(name, **kwargs)
        if not isinstance(handle, VisaHandle):
            raise TypeError(f'Invalid visa handle {type(handle)}')
        self._handle = handle
        self._get_cmd = str(get_cmd)
        self._set_cmd = str(set_cmd)
        self._get_parser = get_parser
        self._set_parser = set_parser
        self._read_after_setting = read_after_setting
        self._encoding = encoding
        self._delay = query_delay

    def parse(self, value: Any) -> Any:
        if isinstance(self._set_parser, Callable):
            return self._set_parser(value)
        return super().parse(value)

    def before_set(self, current: Any, next: Any) -> None:
        if len(self._set_cmd) > 0:
            self._handle.write(self._set_cmd.format(next), self._encoding)
            if self._read_after_setting:
                self._handle.read()
        return super().before_set(current, next)

    def before_get(self, value: Any) -> Any:
        if len(self._get_cmd) > 0:
            return self._handle.query(self._get_cmd, self._delay)
        return super().before_get(value)

    def interprete(self, value: Any) -> Any:
        if isinstance(self._get_parser, Callable):
            return self._get_parser(value)
        return super().interprete(value)

    def snapshot(self) -> dict:
        return {
            **super().snapshot(),
            'get_cmd': self._get_cmd,
            'set_cmd': self._set_cmd,
        }
