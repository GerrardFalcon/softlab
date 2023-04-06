"""
Submodule to organize dynamic processes


- ``Action``: wrapper of action committed into scheduler
- ``Scheduler``: abstract interface of scheduler, can not be instantiated
                 directly
- ``get_scheduler``: function to get instance of implemented scheduler
- ``Process``: interface of any working process
- ``CompositeProcess``, ``SeriesProcess``, ``ParallelProcess``,
  ``SwitchProcess``, ``SweepProcess``: special implementations of ``Process``
  to achieve compositions of subprocesses
"""

from softlab.huo.scheduler import (
    Action,
    Scheduler,
)
from softlab.huo.impl_scheduler import get_scheduler

from softlab.huo.process import (
    Process,
    CompositeProcess,
    SeriesProcess,
    ParallelProcess,
    SwitchProcess,
    SweepProcess,
)
