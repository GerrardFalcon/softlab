"""
Process interface and common composition implementations
"""
from abc import abstractmethod
from typing import (
    Any,
    Sequence,
    Dict,
    Callable,
    Optional,
    Tuple,
)
import logging
import time
from softlab.tu import (
    Delegated,
    LimitedAttribute,
)
from softlab.jin import Validator
from softlab.shui.data import DataGroup
from softlab.huo.scheduler import Action, Scheduler
from softlab.huo.impl_scheduler import get_scheduler

_logger = logging.getLogger(__name__)

class Process(Delegated):
    """
    Interface of any process

    Properties:
    - name -- name of process, only can be given in creation
    - data_group -- binding data group

    As a subclass of `DelegateAttributes`, this interface supports customized
    attributes. Each attribute is an instance of ``LimitedAttribute``.
    ``add_attribute`` method is used to add such attribute by given unique key,
    validator and initial value.

    The methods need be implemented in derived classes:
    - commit -- commit necessary actions into scheduler
    - is_pending -- whether there are committed by unfinished actions
    - join -- wait until all committed actions finish
    - has_more -- whether there are more actions to run
    - reset -- reset to initial state

    Usage:
    1. create and configure a process
    2. commit actions into scheduler
    3. wait until all committed actions finish
    4. check whether there are more actions, if so, back to step 2
    """

    def __init__(self, name: Optional[str] = None):
        self._name = '' if name is None else str(name)
        self._attributes: Dict[str, LimitedAttribute] = {}
        self.add_delegate_attr_dict('_attributes')
        self._group: Optional[DataGroup] = None

    @property
    def name(self) -> str:
        """Get name of process"""
        return self._name

    def get_data_group(self) -> Optional[DataGroup]:
        """Get binding data group"""
        return self._group

    def set_data_group(self, group: Optional[DataGroup]) -> None:
        """Bind with given data group"""
        if self.is_pending():
            raise RuntimeError(f'Can\'t change data group while pending')
        if group is not None and not isinstance(group, DataGroup):
            raise TypeError(f'Invalid data group type: {type(group)}')
        self._group = group

    data_group = property(get_data_group, set_data_group)

    def add_attribute(self, key: str, 
                      vals: Validator, initial_value: Any) -> None:
        """
        Add an attribute

        Args:
        - key -- the key of attribute, should be unique in one process
        - vals -- the validator of attribute,
        - initial_value -- the initial value of attribute
        """
        if key in self._attributes:
            raise ValueError(f'Already has the attribute with key "{key}"')
        self._attributes[key] = LimitedAttribute(vals, initial_value)

    @abstractmethod
    def commit(self, scheduler: Scheduler) -> bool:
        """Commit actions into scheduler"""
        raise NotImplementedError

    @abstractmethod
    def is_pending(self) -> bool:
        """Whether there are committed-but-unfinished actions"""
        raise NotImplementedError

    @abstractmethod
    def join(self, scheduler: Scheduler) -> bool:
        """Wait until committed actions finish"""
        raise NotImplementedError

    @abstractmethod
    def has_more(self) -> bool:
        """Whether there are more actions to run"""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset to initial state"""
        raise NotImplementedError

    def snapshot(self) -> Dict[str, Any]:
        return {
            'class': self.__class__,
            'name': self.name,
            'pending': self.is_pending(),
            'more': self.has_more(),
        }

def run_process(process: Process, scheduler: Optional[Scheduler] = None, 
                verbose: bool = True) -> Tuple[bool, float]:
    """
    Run a process

    Arguments:
    - process -- the process to run
    - scheduler -- the scheduler to perform running, use ``get_scheduler`` if
                   None is given
    - verbose -- verbose flag

    Returns a tuple of result and cost time
    """
    if not isinstance(process, Process):
        raise TypeError(f'Invalid process type {type(process)}')
    if not isinstance(scheduler, Scheduler):
        scheduler = get_scheduler()
    verbose = bool(verbose)
    if verbose:
        print('---- Run Process ----')
    process.reset()
    if verbose:
        print('Reset process first')
        for key, value in process.snapshot().items():
            print(f'{key}: {value}')
        print()
    t0 = time.perf_counter()
    rst = True
    ticks = 0
    while process.has_more():
        process.commit(scheduler)
        if not process.join(scheduler):
            if verbose:
                print(f'Failed to join after {ticks}th commit')
            rst = False
            break
        ticks += 1
    used = time.perf_counter() - t0
    if verbose:
        print('Succeed' if rst else 'Failed')
        print(f'Commit {ticks} Times')
        print(f'Used {used} s')
        print('---- The End ----')
        print()
    return rst, used

class SimpleProcess(Process):
    """
    Base of simple processes which only concern simple actions

    The derived processes only need to implement asynchronised ``body``
    method to achieve process action. If a simple process is aborted before
    finish (i.e. ``reset`` is called), the aborting signal can be obtained
    by ``aborting`` porperty.
    """

    def __init__(self, name: Optional[str] = None, **kwargs):
        super().__init__(name, **kwargs)
        self._begin_point = ''
        self._end_point = ''
        self._finished = False
        self._running = False
        self._aborting = False

    @property
    def begin_point(self) -> str:
        """Get begin point of process"""
        return self._begin_point
    
    @begin_point.setter
    def begin_point(self, point: str) -> None:
        """Set begin point, can't be called while pending"""
        if self._running:
            raise RuntimeError('Can\'t set begin point while pending')
        self._begin_point = str(point)

    @property
    def end_point(self) -> str:
        """
        Get end point of process

        Notice that end point is generated when ``commit`` is called, it 
        can't be set arbitrarily.
        """
        return self._end_point
    
    @property
    def aborting(self) -> bool:
        """Aborting signal"""
        return self._aborting

    @abstractmethod
    async def body(self) -> None:
        """Process action body, need implementation"""
        pass

    async def _run(self) -> None:
        if not self._finished:
            try:
                await self.body()
                self._finished = not self._aborting
            finally:
                self._begin_point = ''
                self._running = False
                self._aborting = False

    def reset(self) -> None:
        if self._running:
            self._aborting = True
        else:
            self._finished = False

    def commit(self, scheduler: Scheduler) -> bool:
        if not self._finished and not self._running:
            point = scheduler.acquire_point()
            rst = scheduler.commit_action(Action(
                self.begin_point, point, func=self._run
            ))
            if rst:
                self._running = True
                self._aborting = False
                self._end_point = point
            return rst
        return False

    def is_pending(self) -> bool:
        return self._running

    def join(self, scheduler: Scheduler) -> bool:
        if len(self._end_point) > 0:
            return scheduler.wait_point(self._end_point)
        return False

    def has_more(self) -> bool:
        return not self._finished

class CompositeProcess(Process):
    """
    Process to hold a sequence of subprocesses

    This is super class of all composited process, it is designed to be an
    iterable class.
    """

    def __init__(self, processes: Sequence[Process] = [],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        self._children: list[Process] = []
        self._iter_index = 0
        if isinstance(processes, Sequence):
            for proc in processes:
                self.add(proc)

    def set_data_group(self, group: DataGroup) -> None:
        """Override data_group setting to synchronize with subprocesses"""
        super().set_data_group(group)
        for child in self._children:
            child.set_data_group(group)

    def add(self, child: Process) -> None:
        """Add a new subprocess"""
        if not isinstance(child, Process):
            raise TypeError(f'Invalid process type {type(child)}')
        self._children.append(child)
        if isinstance(self.data_group, DataGroup):
            child.set_data_group(self.data_group)

    def clear(self) -> None:
        """Clear all subprocesses"""
        self._children = []
        self._iter_index = 0

    def __len__(self) -> int:
        """Get count of subprocesses"""
        return len(self._children)

    def __getitem__(self, index: int) -> Process:
        """Get subprocess at given index"""
        return self._children[index]

    def __iter__(self) -> Any:
        """Start iteration"""
        self._iter_index = 0
        return self

    def __next__(self) -> Process:
        """Iterate sequence"""
        if self._iter_index < len(self._children):
            self._iter_index += 1
            return self._children[self._iter_index - 1]
        else:
            raise StopIteration

    def snapshot(self) -> Dict[str, Any]:
        snapshot = super().snapshot()
        snapshot['children'] = [
            child.snapshot()
            for child in self._children
        ]
        return snapshot

class SeriesProcess(CompositeProcess):
    """
    Implementation of composited process, the subprocesses are run sequentially
    """

    def __init__(self, processes: Sequence[Process] = [],
                 name: Optional[str] = None) -> None:
        super().__init__(processes, name)
        self._index = 0

    def commit(self, scheduler: Scheduler) -> bool:
        while self._index < len(self):
            proc: Process = self[self._index]
            if proc.is_pending():
                _logger.warn(f'Child {proc.name} of {self.name} is pending')
                return False
            elif not proc.has_more():
                self._index += 1
                continue
            else:
                return proc.commit(scheduler)
        _logger.warn(f'All children of {self.name} has done')
        return False

    def is_pending(self) -> bool:
        if self._index < len(self):
            return self[self._index].is_pending()
        return False

    def join(self, scheduler: Scheduler) -> bool:
        if self._index < len(self):
            proc: Process = self[self._index]
            if proc.is_pending():
                return proc.join(scheduler)
        return True

    def has_more(self) -> bool:
        if self._index < len(self):
            proc: Process = self[self._index]
            if proc.is_pending() or proc.has_more():
                return True
            else:
                return self._index < len(self) - 1
        return False

    def reset(self) -> None:
        for child in self:
            child.reset()
        self._index = 0

class ParallelProcess(CompositeProcess):
    """
    Implementation of composited process, the subprocesses are run concurrently
    """

    def __init__(self, processes: Sequence[Process] = [],
                 name: Optional[str] = None) -> None:
        super().__init__(processes, name)

    def commit(self, scheduler: Scheduler) -> bool:
        rst: bool = False
        for child in self:
            if child.is_pending() or not child.has_more():
                continue
            if child.commit(scheduler):
                rst = True
        return rst

    def is_pending(self) -> bool:
        for child in self:
            if child.is_pending():
                return True
        return False

    def join(self, scheduler: Scheduler) -> bool:
        rst = False
        for child in self:
            if child.is_pending():
                if child.join(scheduler):
                    rst = True
        return rst

    def has_more(self) -> bool:
        for child in self:
            if child.is_pending() or child.has_more():
                return True
        return False

    def reset(self) -> None:
        for child in self:
            child.reset()

class SwitchProcess(CompositeProcess):
    """
    Implementaion of composited process, only run one subprocess selected by
    a given switcher
    """

    def __init__(self, switcher: Optional[Callable] = None,
                 processes: Sequence[Process] = [],
                 name: Optional[str] = None) -> None:
        super().__init__(processes, name)
        self._switcher: Optional[Callable] = None
        self.switcher = switcher
        self._current: Optional[Process] = None
        self._decided = False

    @property
    def switcher(self) -> Optional[Callable]:
        return self._switcher

    @switcher.setter
    def switcher(self, sw: Callable) -> None:
        if not isinstance(sw, Callable):
            raise TypeError(f'Switcher needs to be callable: {type(sw)}')
        self._switcher = sw

    def commit(self, scheduler: Scheduler) -> bool:
        if self._current is None and isinstance(self._switcher, Callable) \
                and not self._decided:
            self._decided = True
            try:
                index = int(self._switcher(self.data_group))
                assert(index >= 0 and index < len(self))
            except Exception as e:
                _logger.warn(f'Failed to get valid index by switcher: {e}')
                return False
            self._current = self[index]
            return self._current.commit(scheduler)
        return False

    def is_pending(self) -> bool:
        if isinstance(self._current, Process):
            return self._current.is_pending()
        return False

    def join(self, scheduler: Scheduler) -> bool:
        if isinstance(self._current, Process):
            return self._current.join(scheduler)
        return False

    def has_more(self) -> bool:
        if isinstance(self._current, Process):
            return self._current.has_more()
        return not self._decided

    def reset(self) -> None:
        for child in self:
            child.reset()
        self._current = None
        self._decided = False

class SweepProcess(Process):
    """
    A sweep loop with a loop body and a callable sweeper.
    
    The sweeper is used in every beginning of loop, it takes two arguments:
    1. the corresponding data group;
    2. the body process, in order to adjust the body for next loop.

    The sweeper returns a bool value to decide whether to continue loop,
    True means continue, False means finished.
    """

    def __init__(self, sweeper: Callable, body: Process,
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        if not isinstance(body, Process):
            raise TypeError(f'Sweep body must be a process: {type(body)}')
        self._body = body
        if not isinstance(sweeper, Callable):
            raise TypeError(f'Sweeper must be callable: {type(sweeper)}')
        self._sweeper = sweeper
        self._in_loop = False
        self._finished = False

    def set_data_group(self, group: DataGroup) -> None:
        """Override to synchronize with sweep body"""
        super().set_data_group(group)
        self._body.set_data_group(group)

    def commit(self, scheduler: Scheduler) -> bool:
        if self._in_loop:
            return self._body.commit(scheduler)
        elif not self._finished:
            try:
                decision = bool(self._sweeper(self.data_group, self._body))
            except Exception as e:
                _logger.critical(f'Failed to call sweeper: {e}')
                return False
            if decision:
                self._in_loop = True
                self._body.reset()
                return self._body.commit(scheduler)
            else:
                self._finished = True
        return False

    def is_pending(self) -> bool:
        if self._in_loop:
            return self._body.is_pending()
        return False

    def join(self, scheduler: Scheduler) -> bool:
        if self._in_loop:
            rst = self._body.join(scheduler)
            if not self._body.has_more():
                self._in_loop = False
            return rst
        return self._finished

    def has_more(self) -> bool:
        return not self._finished

    def reset(self) -> None:
        self._body.reset()
        self._in_loop = False
        self._finished = False

if __name__ == '__main__':
    import asyncio
    from softlab.jin import ValString

    class SaluteProcess(SimpleProcess):
        def __init__(self, name: Optional[str] = None, **kwargs):
            super().__init__(name, **kwargs)
            self.add_attribute('subject', ValString(1), 'World')

        async def body(self) -> None:
            print(f'Hello {self.subject()}')
            await asyncio.sleep(1.0)

    class SequenceSaluteProcess(Process):
        def __init__(self, subjects: Sequence[str],
                     name: Optional[str] = None, **kwargs):
            super().__init__(name, **kwargs)
            self._subjects: list[str] = []
            self._index = 0
            self._point = ''
            for subject in subjects:
                self.add(subject)

        def add(self, subject: str) -> None:
            self._subjects.append(str(subject))

        async def salute(self) -> None:
            if self._index >= 0 and self._index < len(self._subjects):
                print(f'Hello {self._subjects[self._index]}')
                await asyncio.sleep(1.0)
                self._index += 1

        def reset(self) -> None:
            self._index = 0
            self._point = ''

        def commit(self, scheduler: Scheduler) -> bool:
            if self._index == 0 and len(self._subjects) > 0 \
                    and len(self._point) == 0:
                points = scheduler.acquire_points(len(self._subjects))
                assert(len(points) == len(self._subjects))
                for i in range(len(points)):
                    if not scheduler.commit_action(Action(
                        '' if i == 0 else points[i-1], points[i],
                        func=self.salute,
                    )):
                        return False
                self._point = points[-1]
                return True
            return False

        def is_pending(self) -> bool:
            return len(self._point) > 0

        def join(self, scheduler: Scheduler) -> bool:
            if len(self._point) > 0:
                rst = scheduler.wait_point(self._point)
                self._point = ''
                return rst
            return False

        def has_more(self) -> bool:
            return self._index < len(self._subjects)

    class SubjectSweeper:
        def __init__(self, subjects: Sequence[str] = []) -> None:
            self._subjects = list(subjects)
            self._index = 0

        def reset(self):
            self._index = 0

        def __call__(self, _: DataGroup, proc: SaluteProcess) -> bool:
            if self._index < len(self._subjects):
                proc.subject(self._subjects[self._index])
                self._index += 1
                return True
            else:
                return False

    sch = get_scheduler()
    sch.start()
    print(sch.snapshot())
    names = ['aaa', 'bbb', 'ccc', 'Suzhou', 
             'China', 'Asia', 'Earth', 'universe']
    print(names)
    print('Use single sequence process')
    proc = SequenceSaluteProcess(names, 'single_seq')
    print(f'Create process: {proc.snapshot()}')
    t0 = time.perf_counter()
    proc.commit(sch)
    print(f'After commit: {proc.snapshot()}')
    proc.join(sch)
    print(f'After join: {proc.snapshot()}')
    print('Used {} s'.format(time.perf_counter() - t0))
    print()

    print('Use serial of separated processes')
    processes = [SaluteProcess(f'sep{i}') for i in range(len(names))]
    for i in range(len(names)):
        processes[i].subject(names[i])
    series = SeriesProcess(processes, 'series')
    print(f'Create series process: {series.snapshot()}')
    run_process(series, sch)
    print()

    print('Use parallel of separated processes')
    parallel = ParallelProcess(processes, 'parallel')
    print(f'Create parallel process: {parallel.snapshot()}')
    run_process(parallel, sch)
    print()

    print('Use switch process')
    sw = SwitchProcess(lambda x: 5, processes, 'switch')
    print(f'Create switch process: {sw.snapshot()}')
    run_process(sw, sch)
    print()

    print('Use sweep process')
    sweep = SweepProcess(
        SubjectSweeper(names), SaluteProcess('salute'), 'sweep')
    print(f'Create sweep process: {sweep.snapshot()}')
    run_process(sweep, sch)
    print()
