"""
Common interface of backend to any database
"""

from typing import (
    Any,
    Optional,
    Dict,
    Sequence,
)
from enum import Enum
from abc import abstractmethod
from functools import wraps

_MAX_ERROR_CNT = 10
"""Maximum count of pending errors"""

class DatabaseBackend():
    """
    Abstract definition of any database backend interface

    Arguments:
    - type -- backend type, given by derived classes

    Properties:
    - backend_type -- type of backend, read-only
    - arguments -- connection arguments, given in connection
    - status -- status of backend, changed due to actions
    - connected -- whether the backend is connected, status classification
    - just_succeeded -- whether the last action succeeded, status classification
    - just_failed -- whether the last action failed, status classification
    - errors -- list of errors, generated during action, can be cleared by user
    - last_error -- last error, generated during action, can be cleared by user

    Actions for user:
    - connect -- connect with given arguments
    - disconnect -- disconnect with backend
    - clear_errors -- clear existing errors

    Methods need be implemented by derived class:
    - connect_impl -- implementaion of actual connection
    - disconnect_impl -- implementation of actual disconnection

    Methods used by derived class to change status:
    - mark_success -- mark status to succeeded when action just succeeds
    - record_error -- mark status to failed and record generated error
    """

    class Status(Enum):
        """Status enum of ``DatabaseBackend``"""
        NotConnected = 0
        ConnectionFailed = 1
        Connected = 2
        ActionSucceeded = 3
        ActionFailed = 4

    def __init__(self, type: str) -> None:
        self._type = str(type)
        self._arguments = {}
        self._status = self.Status.NotConnected
        self._errors = []
    
    @property
    def backend_type(self) -> str:
        """Get type of backend"""
        return self._type
    
    @property
    def arguments(self) -> Dict[str, Any]:
        """Get connection arguments"""
        return self._arguments
    
    @property
    def status(self) -> Status:
        """Get backend status"""
        return self._status
    
    @property
    def connected(self) -> bool:
        """Whether the backend is connected"""
        return self._status in [
            self.Status.Connected,
            self.Status.ActionSucceeded, self.Status.ActionFailed]

    @property
    def just_succeeded(self) -> bool:
        """Whether the last action succeeded"""
        return self._status in [
            self.Status.Connected, self.Status.ActionSucceeded]

    @property
    def just_failed(self) -> bool:
        """Whether the last action failed"""
        return self._status in [
            self.Status.ConnectionFailed, self.Status.ActionFailed]

    @property
    def errors(self) -> Sequence[str]:
        """Get all pending errors"""
        return self._errors

    @property
    def last_error(self) -> str:
        """Get last error"""
        if len(self._errors) > 0:
            return self._errors[-1]
        else:
            return ''

    def connect(self, args: Optional[Dict[str, Any]] = None) -> bool:
        """Connect to the backend"""
        if self.connected:
            self.disconnect()
        if isinstance(args, Dict):
            self._arguments = args
        rst = self.connect_impl(self._arguments)
        if rst:
            self._status = self.Status.Connected
        return rst

    def disconnect(self) -> None:
        """Disconnect from the backend"""
        self.disconnect_impl()
        self._status = self.Status.NotConnected

    def clear_errors(self) -> None:
        """Clear all pending errors"""
        self._errors.clear()

    @abstractmethod
    def connect_impl(self, args: Dict[str, Any]) -> bool:
        """Actual connection, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    @abstractmethod
    def disconnect_impl(self) -> bool:
        """Actual disconnection, implemented in derived class"""
        raise NotImplementedError(
            'This method must be implemented in derived class')

    def mark_success(self) -> None:
        """Mark status to succeeded when the action succeeds"""
        if self.connected:
            self._status = self.Status.ActionSucceeded
        else:
            raise ConnectionError('The backend is not connected')

    def record_error(self, err: str) -> None:
        """Mark status to failed and record generated error"""
        self._errors.append(err)
        while len(self._errors) > _MAX_ERROR_CNT:
            self._errors.pop(0)
        if self.connected:
            self._status = self.Status.ActionFailed
        else:
            self._status = self.Status.ConnectionFailed

    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot of backend"""
        return {
            'class_type': self.__class__,
            'backend_type': self.backend_type,
            'arguments': self.arguments,
            'status': self.status,
            'errors': self.errors,
        }

def catch_error(failed_return: Any = None, action: Optional[str] = None):
    """
    Decoration to auto catch exception as error

    Arguments:
    - failed_return -- return value in case of failure
    - action -- action name in generated error, use function name as default
    """
    def wrapper(func):
        @wraps(func)
        def _wrapper(self: DatabaseBackend, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                func_action = str(action)
                if len(func_action) == 0:
                    func_action = func.__name__
                self.record_error(f'Failed to {func_action}: {e!r}')
                return failed_return
        return _wrapper
    return wrapper
