"""
Basic components in proc module
"""
from abc import abstractmethod
from typing import (
    Any,
    Sequence,
    Dict,
    Callable,
    Tuple,
    Optional,
)

class Action():
    """
    Action information

    Arguments:
    begin_point -- beginning point key
    end_point -- end point key
    to_thread -- whether the action should be run in a separate thread
    func -- corresponding function of action
    args -- sequence of arguments of function
    kwargs -- keyword arguments of function

    Properties:
    begin_point -- beginning point key
    end_point -- end point key
    body -- tuple of action function, arguments and keyword arguments
    to_thread -- whether the action should be run in separate thread
    """
    def __init__(self, begin_point: str, end_point: str,
                 to_thread: bool = False,
                 func: Callable = lambda : None,
                 *args: Any, **kwargs: Any) -> None:
        self._begin = str(begin_point)
        self._end = str(end_point)
        self._thread = to_thread if isinstance(to_thread, bool) else False
        if isinstance(func, Callable):
            self._body = (func, args, kwargs)
        else:
            raise TypeError(f'Action is not callable: {type(func)}')

    @property
    def begin_point(self) -> str:
        """Get beginning point key"""
        return self._begin

    @property
    def end_point(self) -> str:
        """Get end point key"""
        return self._end

    @property
    def body(self) -> Tuple[Callable, Sequence[Any], Dict[Any, Any]]:
        """Get tuple of action function, arguments and keyword arguments"""
        return self._body

    @property
    def to_thread(self) -> bool:
        """Whether the action should be run in separate thread"""
        return self._thread

    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot"""
        return {
            'type': self.__class__,
            'begin': self.begin_point,
            'end': self.end_point,
            'func': self.body[0].__name__,
            'to_thread': self.to_thread,
        }
        
class Scheduler():
    """
    Abstract interface of scheduler

    The methods need be implemented by subclass:
    start -- start scheduler
    stop -- stop scheduler
    is_running --- whether the scheduler is running
    acquire_point -- acquire key of a new control point
    commit_action -- commit an action into scheduler
    wait_point -- wait until the given point finished
    """

    @abstractmethod
    def start(self) -> bool:
        """
        Start scheduler

        Return: whether the scheduler is started
        """
        raise NotImplementedError('Must be implemented by subclass')

    @abstractmethod
    def stop(self) -> None:
        """Stop scheduler"""
        raise NotImplementedError('Must be implemented by subclass')

    @abstractmethod
    def is_running(self) -> bool:
        """Whether the scheduler is running"""
        raise NotImplementedError('Must be implemented by subclass')

    @abstractmethod
    def acquire_point(self) -> str:
        """Acquire a key of a new control point"""
        raise NotImplementedError('Must be implemented by subclass')

    def acquire_points(self, count: int) -> Tuple[str]:
        """Acquire given count of new control points"""
        cnt = int(count)
        if cnt > 0:
            return tuple(map(
                lambda _: self.acquire_point(),
                range(cnt),
            ))
        else:
            raise TypeError(f'Invalid count of points: {count}')

    @abstractmethod
    def commit_action(self, action: Action) -> bool:
        """
        Commit an action into scheduler
        
        Arguments:
        action -- the committed action

        Return: whethe the action is committed into the scheduler
        """
        raise NotImplementedError('Must be implemented by subclass')

    @abstractmethod
    def wait_point(self, point: str, 
                   timeout: Optional[float] = None) -> Optional[bool]:
        """
        Wait until the given point finished

        Arguments:
        point -- key of waiting control point
        timeout -- maximum waiting time, unit: s, optional, ``None`` means
                   to wait until the given point is done

        Return:
        None -- timeout
        True -- the control point is satisfied
        False -- the control point has failed
        """
        raise NotImplementedError('Must be implemented by subclass')

    @abstractmethod
    def clear_done_points(self) -> None:
        """Clear done control points"""
        raise NotImplementedError('Must be implemented by subclass')

    @abstractmethod
    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot"""
        return {
            'type': __class__,
            'implemented': False,
        }
