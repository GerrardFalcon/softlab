"""
Definitions of basic DSP objects, including:
- ``Signal`` class
- ``Wavement`` class
- Composition implementations of ``Signal``
"""

from abc import abstractmethod
from typing import (
    Any,
    Sequence,
    Union,
    Optional,
)
from softlab.jin import (
    Validator,
    ValType,
)
from softlab.tu import (
    Delegated,
    LimitedAttribute,
)
import numpy as np

class Signal(Delegated):
    """
    Abstract class representing a signal

    A subclass can define a specific signal from two aspects:
        - implement `evaluate` method
        - add specific attributes, the `Signal` class is derived from
          `DelegateAttributes`, the added attributes can be called
          by its name, a.k.a `<obj>.<attr_name>` can be read and written
          as well

    Args:
        - name, the name of signal, optional
    """
    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__()
        self._name = name if isinstance(name, str) else ''
        self._attributes = {}
        self.add_delegate_attr_dict('_attributes')

    @property
    def name(self) -> str:
        return self._name

    def add_attribute(self, key: str, 
                      vals: Validator, initial_value: Any) -> None:
        """
        Add an attribute to the signal

        Args:
            - key, the key of attribute, should be unique in one signal
            - vals, the validator of attribute,
            - initial_value, the initial value of attribute
        """
        if key in self._attributes:
            raise ValueError(f'Already has the attribute with key "{key}"')
        self._attributes[key] = LimitedAttribute(vals, initial_value)

    def __call__(self, ts: np.ndarray) -> np.ndarray:
        """
        Return signal values according to input timestamps
        
        The signal instance is directly callable
        """
        return self.evaluate(ts)

    def __repr__(self) -> str:
        prefix = f'{self.name} ' if len(self.name) > 0 else ''
        return f'{prefix}{self.__class__}'

    @abstractmethod
    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        """Return signal values according to input timestamps"""
        return np.zeros_like(ts)

class Wavement:
    """
    Wavement is a pair of a time sequence and value sequece

    Arguments:
    - ts -- time sequence
    - ys -- value sequence
    """
    def __init__(self, ts: np.ndarray, ys: np.ndarray):
        if not isinstance(ts, np.ndarray) or not isinstance(ys, np.ndarray):
            raise TypeError('ts and ys must be numpy ndarray')
        t_shape = ts.shape
        y_shape = ys.shape
        if len(t_shape) != 1 or len(y_shape) != 1 or \
                t_shape[0] < 2 or t_shape[0] != y_shape[0]:
            raise ValueError(f'Shapes of ts and ys are invalid: '
                             f'{t_shape} {y_shape}')
        if ts.dtype != float:
            raise TypeError(f'Invalid time type: {ts.dtype}')
        valid = True
        invalid_idx = -1
        for i in range(t_shape[0] - 1):
            if not ts[i] < ts[i+1]:
                invalid_idx = i
                valid = False
                break
        if not valid:
            raise ValueError(f'Time sequence is invalid at {invalid_idx}')
        self._ts = ts
        self._ys = ys
        self._pos = 0
    
    def __len__(self):
        """Get length of wavement"""
        return self._ts.shape[0]

    def __getitem__(self, index):
        return (self._ts[index], self._ys[index])

    def __copy__(self):
        """Make a copy of wavement"""
        return Wavement(self._ts.copy(), self._ys.copy())

    def __add__(self, other):
        """
        Override add operator:
        - return a combined wavement if ``other`` is also a wavement
        - add other to value sequence otherwise
        """
        if isinstance(other, Wavement):
            length = len(self) + len(other)
            ts = np.zeros((length,))
            ts[:len(self)] = self._ts
            ts[len(self):] = other.times + (self.end + \
                self.interval - other.offset)
            ys = np.zeros((length,))
            ys[:len(self)] = self._ys
            ys[len(self):] = other.values
            return Wavement(ts, ys)
        else:
            self._ys = self._ys + other

    def __radd__(self, other):
        """Override right add operator"""
        self._ys = self._ys + other

    def __sub__(self, other):
        """Override substract operator"""
        self._ys = self._ys - other

    def __mul__(self, other):
        """Override multiply operator"""
        self._ys = self._ys * other

    def __truediv__(self, other):
        """Override fraction operator"""
        self._ys = self._ys / other

    def __pow__(self, other):
        """Override power operator"""
        self._ys = np.power(self._ys, other)

    def __iter__(self):
        """Start iteration of wavement"""
        self._pos = 0
        return self

    def __next__(self):
        """Get next point of wavement, return tuple of time and value"""
        if self._pos < len(self):
            rst = (self._ts[self._pos], self._ys[self._pos])
            self._pos += 1
            return rst
        else:
            raise StopIteration

    @property
    def offset(self) -> float:
        """Get time offset"""
        return self._ts[0]

    @offset.setter
    def offset(self, t: float) -> None:
        """Set time offset"""
        self._ts = self._ts + (t - self._ts[0])

    @property
    def end(self) -> float:
        """Get end of time"""
        return self._ts[-1]

    @property
    def duration(self) -> float:
        """Get time duration of wavement"""
        return self._ts[-1] - self._ts[0]

    @property
    def interval(self) -> float:
        """Get time interval"""
        return self._ts[1] - self._ts[0]

    @property
    def times(self) -> np.ndarray:
        """Get time sequence"""
        return self._ts

    @property
    def values(self) -> np.ndarray:
        """Get value sequence"""
        return self._ys

    def extend(self, other: "Wavement", delay: float = 0.0) -> None:
        """
        Extend another wavement

        Arguments:
        - other -- the wavement to append
        - delay -- delay between two wavements, should be positive, use interval
                   if it's invalid (default case)
        """
        if not isinstance(other, Wavement):
            raise TypeError(f'Invalid wavement type: {type(other)}')
        d = delay if isinstance(delay, float) and delay > 0.0 else self.interval
        length = len(self) + len(other)
        self._ts.resize((length,))
        self._ts[len(self):] = other.times + (self.end + d - other.offset)
        self._ys.resize((length,))
        self._ys[len(self):] = other.values

    def delay(self, t: float) -> "Wavement":
        """Move time to generate a new wavement"""
        return Wavement(self._ts + t, self._ys)

    def scale(self, s: float) -> "Wavement":
        """Scale value to generate a new wavement"""
        return Wavement(self._ts, self._ys * s)

    def stretch(self, s: float, keep_offset=False) -> "Wavement":
        """
        Stretch time to generate a new wavement

        Arguments:
        - s -- stretch factor, must be positive
        - keep_offset -- whether to keep current offset, default is False
        """
        if s > 0.0:
            ts = self._ts * s
            if keep_offset:
                ts = ts - ts[0] + self.offset
            return Wavement(ts, self._ys)
        else:
            raise ValueError(f'Invalid stretch factor {s}')

    def window(self, win: Signal, ignore_offset=False) -> "Wavement":
        """
        Apply a signal window to generate a new wavement

        Arguments:
        - win -- signal window
        - ignore_offset -- whether to ignore offset, default is False
        """
        if not isinstance(win, Signal):
            raise TypeError(f'Invalid type of window: {type(win)}')
        d = self.offset if ignore_offset else 0.0
        return Wavement(self._ts, self._ys * win.evaluate(self._ts - d))

    def quantize(self, step: float, mode: str = '',
                 min: float = -np.Inf, max: float = np.Inf) -> "Wavement":
        """
        Quantize wavement to generate a new wavement

        Arguments:
        - step -- quantization step, must be positive
        - mode -- quantization mode, default is 'floor', can be specified
                  to be 'round' or 'ceil'
        - min -- minimal limit
        - max -- maximal limit
        """
        if step > 0.0 and min < max:
            if mode == 'round':
                ys = np.round(self._ys / step) * step
            elif mode == 'ceil':
                ys = np.ceil(self._ys / step) * step
            else:
                ys = np.floor(self._ys / step) * step
            if min > -np.Inf:
                ys[ys < min] = min
            if max < np.Inf:
                ys[ys > max] = max
            return Wavement(self._ts, ys)
        else:
            raise ValueError(f'Invalid setting: {step}, {min}, {max}')

class SumSignal(Signal):
    """
    A signal representing sum of several signals

    Args:
        - signals, list of signals to sum up
    """
    def __init__(self, signals: Sequence[Signal],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        self._signals = []
        for sig in signals:
            if isinstance(sig, Signal):
                self._signals.append(sig)
        if len(self._signals) == 0:
            raise ValueError('No valid signal input')
    
    def append(self, sig: Signal) -> None:
        """Add a signal into sum list"""
        if isinstance(sig, Signal):
            self._signals.append(sig)
    
    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        rst = np.zeros_like(ts)
        for sig in self._signals:
            if isinstance(sig, Signal):
                rst = rst + sig.evaluate(ts)
        return rst

class ConcatSignal(Signal):
    """
    A signal representing concatenation of several signals

    Args:
        - signals, list of signals to concatenate
    """
    def __init__(self, signals: Sequence[Signal],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        self._signals = []
        for sig in signals:
            if isinstance(sig, Signal):
                self._signals.append(sig)
        if len(self._signals) == 0:
            raise ValueError('No valid signal input')
    
    def append(self, sig: Signal) -> None:
        """Add a signal into sum list"""
        if isinstance(sig, Signal):
            self._signals.append(sig)
    
    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        rst = np.ones_like(ts)
        for sig in self._signals:
            if isinstance(sig, Signal):
                rst = rst * sig.evaluate(ts)
        return rst

class FactorSignal(Signal):
    """
    A signal representing a base signal multiplied by a factor

    Args:
        - signal, base signal, related to a read-only attribute 'base'
        - factor, factor value, related to an attribute 'factor'
    """
    def __init__(self, signal: Signal, factor: Union[float, complex],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        if isinstance(signal, Signal):
            self._base = signal
        else:
            raise TypeError(f'Input signal type error: {type(signal)}')
        self.add_attribute(
            'factor',
            ValType((int, float, np.complexfloating)),
            factor,
        )

    @property
    def base(self) -> Signal:
        return self._base

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        if isinstance(self._base, Signal):
            return self.factor() * self._base.evaluate(ts)

class OffsetSignal(Signal):
    """
    A signal representing a base signal plus an offset

    Args:
        - signal, base signal, related to a read-only attribute 'base'
        - offset, offset value, related to an attribute 'offset'
    """
    def __init__(self, signal: Signal, offset: Union[float, complex],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        if isinstance(signal, Signal):
            self._base = signal
        else:
            raise TypeError(f'Input signal type error: {type(signal)}')
        self.add_attribute(
            'offset',
            ValType((int, float, np.complexfloating)),
            offset,
        )

    @property
    def base(self) -> Signal:
        return self._base

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        if isinstance(self._base, Signal):
            return self.offset() + self._base.evaluate(ts)

class ReciprocalSignal(Signal):
    """
    A signal representing a fraction in which a factor is numerator
    and a signal is denominator

    Args:
        - signal, denominator signal, related to a read-only attribute 'base'
        - factor, numerator value, related to an attribute 'factor'
    """
    def __init__(self, signal: Signal, factor: Union[float, complex],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        if isinstance(signal, Signal):
            self._base = signal
        else:
            raise TypeError(f'Input signal type error: {type(signal)}')
        self.add_attribute(
            'factor',
            ValType((int, float, np.complexfloating)),
            factor,
        )

    @property
    def base(self) -> Signal:
        return self._base

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        if isinstance(self._base, Signal):
            return self.factor() / self._base.evaluate(ts)
