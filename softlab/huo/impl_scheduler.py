"""
Implementation of scheduler
"""
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
)
import asyncio
import functools
import logging
import uuid
from softlab.huo.scheduler import (
    Action,
    Scheduler,
)
import time

_logger = logging.getLogger(__name__) # prepare logger
_scheduler: Optional['_SchedulerImpl'] = None # scheduler instance

class _CtrlPoint():
    """
    Control point

    Arguments:
    fut -- Future instance corresponding to the control point

    Properties:
    id -- ID of control point
    is_done -- whether the control point is finished
    status -- current status of control point, 3 options:
        None: not done
        True: finished successfully
        False: failed, including cancelled case
    previous_actions -- tuple of previous action IDs
    post_actions -- tuple of post action IDs
    
    Public methods:
    add_previous -- add a previous action
    add_post -- add a post action
    finish -- finish control point
    cancel -- cancel control point
    wait -- wait control point to be finished
    """

    def __init__(self, fut: asyncio.Future):
        self._id = str(uuid.uuid4())
        if not isinstance(fut, asyncio.Future):
            raise TypeError(f'Invalid future type: {type(fut)}')
        self._future = fut
        self._count = 0
        self._previous = []
        self._posts = []

    @property
    def id(self) -> str:
        """Get ID"""
        return self._id

    @property
    def is_done(self) -> bool:
        """Whether the control point is finished"""
        return self._future.done()

    @property
    def status(self) -> Optional[bool]:
        """Get current status of control point"""
        if not self._future.done():
            return None
        elif self._future.exception() != None:
            return False
        else:
            return True

    @property
    def previous_actions(self) -> Tuple[str]:
        """Get tuple of previous actions"""
        return tuple(self._previous)

    @property
    def post_actions(self) -> Tuple[str]:
        """Get tuple of post actions"""
        return tuple(self._posts)

    def add_previous(self, id: str) -> None:
        """
        Add a previous action

        Arguments:
        id -- action ID
        """
        act_id = str(id)
        if len(act_id) == 0 or act_id in self._previous:
            raise ValueError(f'Action ID "{id}" is invalid')
        self._previous.append(act_id)
        self._count += 1

    def add_post(self, id: str) -> None:
        """
        Add a post action

        Arguments:
        id -- action ID
        """
        act_id = str(id)
        if len(act_id) == 0 or act_id in self._posts:
            raise ValueError(f'Action ID "{id}" is invalid')
        self._posts.append(act_id)

    def finish(self, exp: Optional[Exception] = None) -> None:
        """
        Finish control point

        Arguments:
        exp -- exception happened during the action, optional, ``None``
               means success
        """
        if not self._future.done():
            if isinstance(exp, Exception):
                self._future.set_exception(exp)
                _logger.warning(f'Control point {self._id} failed: {exp}')
            else:
                if self._count > 0:
                    self._count -= 1
                    if self._count == 0:
                        self._future.set_result(self._id)
                        _logger.info(f'Control point {self._id} succeeds')

    def cancel(self, src: str = '') -> None:
        """
        Cancel the control point

        Arguments:
        src -- source of cancel action
        """
        if not self._future.done():
            self._future.cancel()
            _logger.warning(f'Control point {self._id} is cancelled by {src}')

    async def wait(self, timeout: Optional[float] = None) -> Optional[bool]:
        """
        Wait for the end of control point

        Arguments:
        timeout -- waiting timeout thread, optional, ``None`` means waiting
                   until the control point finishes

        Returns: status after waiting
        """
        # print(f'Begin waiting {self.id} {timeout}')
        if not self._future.done():
            try:
                await asyncio.wait_for(self._future, timeout)
            except asyncio.TimeoutError:
                _logger.info(f'Timeout {timeout} seconds for {self.id}')
        # print(f'End waiting {self.id} {timeout}')
        return self.status

    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot"""
        return {
            'type': 'CtrlPoint',
            'id': self.id,
            'previous': self.previous_actions,
            'posts': self.post_actions,
            'status': self.status,
        }

def _callback_action(act_id: str, future: asyncio.Future) -> None:
    """Callback of action"""
    if future.done() and isinstance(_scheduler, _SchedulerImpl):
        _scheduler.finish_action(act_id)

class _ActionRunner():
    """
    Runner of an action

    Arguments:
    action -- the action to run
    prev -- previous control point, optional
    post -- post control point, optional

    Properties:
    id -- ID of action runner
    action -- corresponding action
    is_done -- whether the action finished
    status -- current status of action, 3 options:
        None: not finished
        True: finished successfully
        False: failed

    Public methods:
    cancel -- cancel the action
    trigger -- trigger the post control point
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, action: Action, 
                 prev: Optional[_CtrlPoint] = None,
                 post: Optional[_CtrlPoint] = None) -> None:
        self._id = str(uuid.uuid4())
        if not isinstance(action, Action):
            raise TypeError(f'Invalid action type: {type(action)}')
        self._action = action
        self._prev = None
        if isinstance(prev, _CtrlPoint):
            self._prev = prev
            prev.add_post(self.id)
        self._post = None
        if isinstance(post, _CtrlPoint):
            self._post = post
            post.add_previous(self.id)
        self._status: Optional[bool] = None
        self._exp: Optional[Exception] = None
        self._task = loop.create_task(self._run())
        self._task.add_done_callback(
            functools.partial(_callback_action, self.id))

    @property
    def id(self) -> str:
        """Get ID"""
        return self._id

    @property
    def action(self) -> Action:
        """Get corresponding action"""
        return self._action

    @property
    def is_done(self) -> bool:
        """Whether the action is finished"""
        return self._task.done()

    @property
    def status(self) -> Optional[bool]:
        """Get current status of action"""
        return self._status

    def cancel(self) -> None:
        """Cancel the action"""
        if not self._task.done():
            self._status = False
            self._exp = asyncio.CancelledError
            self._task.cancel()

    async def _run(self) -> Any:
        """Action running task"""
        prev = True
        result = None
        if isinstance(self._prev, _CtrlPoint):
            prev = await self._prev.wait()

        if prev:
            func, args, kwargs = self._action.body
            if asyncio.iscoroutinefunction(func):
                func_async = functools.partial(func, *args, **kwargs)
            else:
                async def _wrapped():
                    try:
                        return func(*args, **kwargs)
                    except Exception:
                        raise
                func_async = _wrapped
            try:
                if self._action.to_thread:
                    result = await asyncio.to_thread(func_async)
                else:
                    result = await func_async()
            except Exception as e:
                _logger.error(f'Got exception in {func.__name__}: {e!r}')
                self._exp = e
            self._status = self._exp is None
        else:
            self._status = False

        return result

    def trigger_post(self) -> None:
        """Trigger the post control point"""
        if self._task.done() and isinstance(self._post, _CtrlPoint):
            if self._status:
                self._post.finish()
            elif isinstance(self._exp, Exception):
                self._post.finish(self._exp)
            else:
                self._post.cancel(self.id)

    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot"""
        return {
            'type': 'ActionRunner',
            'id': self.id,
            'action': self.action.snapshot(),
            'status': self.status,
        }

class _SchedulerImpl(Scheduler):
    """Implementation of scheduler"""

    def __init__(self):
        self._points: Dict[str, _CtrlPoint] = {}
        self._runners: Dict[str, _ActionRunner] = {}
        self._running = False
        self._loop = asyncio.get_event_loop()

    def start(self) -> bool:
        """
        Start scheduler

        Return: whether the scheduler is started
        """
        self._running = True
        return True

    def stop(self) -> None:
        """Stop scheduler"""
        for _, runner in self._runners.items():
            runner.cancel() # cancel all runners
        self._runners = {}
        for _, point in self._points.items():
            point.cancel('scheduler') # cancel all points
        self._points = {}
        self._running = False

    def is_running(self) -> bool:
        """Whether the scheduler is running"""
        return self._running

    def acquire_point(self) -> str:
        """Acquire a key of a new control point"""
        point = _CtrlPoint(self._loop.create_future())
        self._points[point.id] = point
        return point.id

    def commit_action(self, action: Action) -> bool:
        """
        Commit an action into scheduler
        
        Arguments:
        action -- the committed action

        Return: whethe the action is committed into the scheduler
        """
        if not self._running:
            _logger.warning(f'Scheduler is not running')
            return False
        if not isinstance(action, Action):
            raise TypeError(f'Invalid type of action: {type(action)}')
        prev = self._points.get(action.begin_point, None)
        if len(action.begin_point) > 0 and prev is None:
            raise ValueError(f'Invalid begin point: {action.begin_point}')
        post = self._points.get(action.end_point, None)
        if len(action.end_point) > 0 and post is None:
            raise ValueError(f'Invalid end point: {action.end_point}')
        runner = _ActionRunner(self._loop, action, prev, post)
        self._runners[runner.id] = runner
        return True

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
        if not self._running: # check running flag
            raise RuntimeError(f'Scheduler is not running')
        key = str(point)
        if len(key) == 0:
            raise ValueError(f'Key of point is empty')
        val = self._points.get(key, None) # get point
        if not isinstance(val, _CtrlPoint):
            raise ValueError(f'Invalid point key {point}')
        if not val.is_done:
            self._loop.run_until_complete(val.wait(timeout))
        return val.status

    def clear_done_points(self) -> None:
        """Clear done control points"""
        self._points = dict(filter(
            lambda pair: not pair[1].is_done,
            self._points.items(),
        ))

    def finish_action(self, act_id: str) -> None:
        """
        Cleanup when the given action finished

        Arguments:
        act_id -- ID of action
        """
        runner = self._runners.pop(act_id, None)
        if isinstance(runner, _ActionRunner):
            runner.trigger_post()

    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot"""
        snap = super().snapshot()
        snap['implemented'] = True
        snap['is_running'] = self.is_running()
        snap['point_count'] = len(self._points)
        snap['done_point_count'] = sum(map(
            lambda pair: 1 if pair[1].is_done else 0,
            self._points.items(),
        ))
        snap['active_point_count'] = len(self._points) \
            - snap['done_point_count']
        snap['action_count'] = len(self._runners)
        return snap

def get_scheduler() -> Scheduler:
    """Get implemented scheduler instance"""
    global _scheduler
    if not isinstance(_scheduler, _SchedulerImpl):
        _scheduler = _SchedulerImpl()
    return _scheduler

if __name__ == '__main__':
    # initialize scheduler
    scheduler = get_scheduler()
    snap = scheduler.snapshot()
    assert(not snap['is_running'])
    print(f'Get schedular: {snap}')

    # start scheduler
    assert(scheduler.start())
    assert(scheduler.is_running())

    # prepare action function
    async def mock_event(event: str, t: float) -> None:
        print(f'Beginning of {event}')
        print(f'Sleeping {t} seconds ...')
        await asyncio.sleep(t)
        print(f'End of {event}')
        print()

    # first flow
    points = scheduler.acquire_points(4)
    end_points = [points[-1]]
    print(points)
    cnt = sum(map(
        lambda action: 1 if scheduler.commit_action(action) else 0,
        map(
            lambda idx: Action(
                '' if idx == 0 else points[idx - 1],
                points[idx], False,
                mock_event, f'A_{idx+1}', 0.5,
            ),
            range(len(points)),
        ),
    ))
    assert(cnt == len(points))
    snap = scheduler.snapshot()
    print(f'Scheduler after flow A: {snap}')
    assert(len(points) == snap['point_count'])
    assert(cnt == snap['action_count'])

    # second flow
    points = scheduler.acquire_points(4)
    end_points.append(points[-1])
    for info in (
        ('', points[0], 'B_1', 0.5),
        (points[0], points[1], 'B_2', 0.5),
        (points[1], points[2], 'B_3', 0.1),
        (points[1], points[2], 'B_4', 0.2),
        (points[1], points[2], 'B_5', 0.3),
        (points[2], points[3], 'B_6', 0.5),
    ):
        assert(scheduler.commit_action(Action(
            info[0], info[1], func=mock_event, event=info[2], t=info[3],
        )))

    # third flow
    points = scheduler.acquire_points(6)
    end_points.append(points[-1])
    for info in (
        ('', points[0], 'C_1', 1.0),
        ('', points[1], 'C_2', 0.2),
        ('', points[1], 'C_3', 0.5),
        (points[0], points[2], 'C_4', 0.5),
        (points[1], points[3], 'C_5', 0.5),
        (points[2], points[4], 'C_6', 0.5),
        (points[3], points[4], 'C_7', 1.0),
        (points[4], points[5], 'C_8', 0.5),
    ):
        assert(scheduler.commit_action(Action(
            info[0], info[1], func=mock_event, event=info[2], t=info[3],
        )))
    assert(scheduler.commit_action(Action(points[2], points[3])))

    # run
    t0 = time.perf_counter()
    print(end_points)
    for idx, point in enumerate(end_points):
        assert(scheduler.wait_point(point))
        print(f'Flow {idx+1} used {time.perf_counter() - t0} seconds')
        print()

    # stop
    snap = scheduler.snapshot()
    assert(snap['active_point_count'] == 0)
    assert(snap['action_count'] == 0)
    print('Scheduler finished all actions and points')
    scheduler.stop()
    assert(not scheduler.is_running())
