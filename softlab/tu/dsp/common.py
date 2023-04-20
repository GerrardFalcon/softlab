"""
Common implementation of signals
"""

from typing import (
    Any,
    Union,
    Optional,
    Callable,
)
from softlab.jin import (
    ValNumber,
    ValType,
)
import numpy as np
from softlab.tu.dsp.base import Signal

class FunctionalSignal(Signal):
    """
    A signal defined by a given function

    Args:
        - name, signal name, optional
        - sig_func, a callable function defining the signal behavior
    """
    def __init__(self, name: Optional[str] = None,
                 sig_func: Callable[[np.ndarray], np.ndarray] = None) -> None:
        super().__init__(name)
        self.sig_func = sig_func

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        """Calling function to get signal values"""
        try:
            return self.sig_func(ts)
        except Exception:
            return super().evaluate(ts)

class FixedSignal(Signal):
    """
    A signal with fixed value

    Args:
        - fixed, the fixed value that signal always returns
    """
    def __init__(self, fixed: Union[float, complex],
                 name: Optional[str] = None) -> None:
        super().__init__(name)
        self.add_attribute(
            'fixed',
            ValType((int, float, np.complexfloating)),
            fixed,
        )

    def __repr__(self) -> str:
        return super().__repr__() + f' ({self.fixed()})'

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        return np.ones_like(ts, dtype=type(self.fixed())) * self.fixed()

class LinearSignal(Signal):
    """
    A signal as linear function of time, a.k.a. ``coeff * time + offset``

    Args:
        - coeff, the coefficient on the time
        - offset, the offset on the output
    """

    def __init__(self, name: Optional[str] = None,
                 coeff: float = 1.0, offset: float = 0.0) -> None:
        super().__init__(name)
        self.add_attribute('coeff', ValNumber(), coeff)
        self.add_attribute('offset', ValNumber(), offset)

    def __repr__(self) -> str:
        return super().__repr__() + f' ({self.coeff()}, {self.offset()})'

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        return self.coeff() * ts + self.offset()

class PeriodicSignal(Signal):
    """
    Abstract class of any periodic signal

    Args:
    - amp -- amplitude of signal, default is 1.0
    - freq -- frequency of signal, unit: Hz, default is 1e3 Hz
    - phase -- initial phase, unit: rad, default is 0 rad
    - dc_offset -- DC offset, default is 0.0

    All three arguments correspond to instance attributes,
    and it also supports cycle, omage (circular frequency) and phase_deg
    (initial phase in degree) attributes.
    """
    def __init__(self, name: Optional[str] = None,
                 amp: float = 1.0,
                 freq: float = 1.0e3,
                 phase: float = 0.0,
                 dc_offset: float = 0.0,
    ) -> None:
        super().__init__(name)
        self.add_attribute('amp', ValNumber(0.0), amp)
        self.add_attribute('freq', ValNumber(1.0e-12), freq)
        self.add_attribute('phase', ValNumber(), phase)
        self.add_attribute('dc_offset', ValNumber(), dc_offset)

    def __repr__(self) -> str:
        return super().__repr__() + ' ({} ± {}, {}Hz, {}deg)'.format(
            self.dc_offset(), self.amp(), self.freq(), self.phase_deg,
        )

    @property
    def cycle(self) -> float:
        """Cycle"""
        return 1.0 / self.freq()

    @cycle.setter
    def cycle(self, c: float) -> None:
        """Set cycle"""
        self.freq(1.0 / c)

    @property
    def omega(self) -> float:
        """Circular frequency"""
        return self.freq() * 2.0 * np.pi

    @omega.setter
    def omega(self, w: float = 6.28e3) -> None:
        """Set circular frequency"""
        self.freq(w / 2.0 / np.pi)

    @property
    def phase_deg(self) -> float:
        """Initial phase in degree"""
        return np.rad2deg(self.phase())

    @phase_deg.setter
    def phase_deg(self, phi: float = 0.0) -> None:
        """Set initial phase in degree"""
        self.phase(np.deg2rad(phi))

class SineSignal(PeriodicSignal):
    """Sine signal with real number"""

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        return self.amp() * np.sin(self.omega * ts + self.phase()) \
             + self.dc_offset()

class ComplexSineSignal(PeriodicSignal):
    """Sine signal with complex number"""

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        angles = self.omega * ts + self.phase()
        return self.amp() * (np.cos(angles) + np.sin(angles) * 1j) \
             + self.dc_offset()

class TriangleSignal(PeriodicSignal):
    """Triangle signal, 0.0 -> amp -> 0.0 in phase 0.0 and offset 0.0 case"""

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        cycles = self.freq() * ts + self.phase() / (2.0 * np.pi)
        frac = np.modf(cycles + 0.5)[0] - 0.5
        return np.abs(frac) * self.amp() * 2.0 + self.dc_offset()

class RampSignal(PeriodicSignal):
    """
    Ramp signal, 0.0 -> amp -> 0.0 in phase 0.0 and offset 0.0 case

    Subclass of PeriodicSignal with an additional argument:
    - width_ratio -- ratio of ramp part, 0.0 ~ 1.0, ramp signal with 0.5 width
                     ratio is equivelant to triangle signal, default is 0.9

    ``width_ratio`` is also an attribute
    """

    def __init__(self, name: Optional[str] = None,
                 width_ratio: float = 0.9,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('width_ratio', ValNumber(0.0, 1.0), width_ratio)

    def __repr__(self) -> str:
        return super().__repr__() + f' {self.width_ratio() * 100.0}%'

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        w = self.width_ratio()
        cycles = self.freq() * ts + self.phase() / (2.0 * np.pi)
        cycles = np.modf(cycles)[0]
        ys = np.zeros_like(cycles)
        if w > 0.0:
            ys[cycles<=w] = cycles[cycles<=w] / w
        if w < 1.0:
            ys[cycles>=w] = (1.0 - cycles[cycles>=w]) / (1.0 - w)
        return ys * self.amp() + self.dc_offset()

class SquareSignal(PeriodicSignal):
    """
    Square signal, a cycle consists of a high level and a low level

    Subclass of PeriodicSignal with an additional argument:
    - width_ratio -- ratio of high part, 0.0 ~ 1.0, default is 0.5

    ``width_ratio`` is also an attribute
    """

    def __init__(self, name: Optional[str] = None,
                 width_ratio: float = 0.5,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('width_ratio', ValNumber(0.0, 1.0), width_ratio)

    def __repr__(self) -> str:
        return super().__repr__() + f' {self.width_ratio() * 100.0}%'

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        cycles = self.freq() * ts + self.phase() / (2.0 * np.pi)
        cycles = np.modf(cycles)[0]
        ys = np.zeros_like(cycles)
        ys[cycles<self.width_ratio()] = self.amp()
        return ys + self.dc_offset()

class PulseSignal(Signal):
    """
    Abstract class of any pulse-like signals

    Arguments:
    - begin -- begin time, unit: s, default is 0.0s
    - duration -- duration of pulse, unit: s, default is 1.0s

    ``begin`` and ``duration`` are also attributes
    """

    def __init__(self, name: Optional[str] = None,
                 begin: float = 0.0,
                 duration: float = 1.0,
                 ) -> None:
        super().__init__(name)
        self.add_attribute('begin', ValNumber(), begin)
        self.add_attribute('duration', ValNumber(0.0), duration)

    def __repr__(self) -> str:
        return super().__repr__() + ' ({}s, {}s)'.format(
            self.begin(), self.duration(),
        )

    def get_valids(self, ts: np.ndarray) -> np.ndarray:
        """Get valid array of input timestamp sequence"""
        return (ts >= self.begin()) & (ts <= self.begin() + self.duration())

class ChirpSignal(PulseSignal):
    """
    Linear chirp signal

    Subclass of ``PulseSignal`` with 4 additional arguments:
    - amp -- amplitude, defalut: 1.0
    - freq_begin -- frequency at the beginning of pulse, unit: Hz, default: 1e3
    - freq_end -- frequency at the end of pulse, unit: Hz, default: 2e3
    - phase -- initial phase, unit: rad, default: 0.0
    - dc_offset -- DC offset, default is 0.0

    These arguments are also attributes
    """

    def __init__(self, name: Optional[str] = None,
                 amp: float = 1.0,
                 freq_begin: float = 1e3, freq_end: float = 2e3,
                 phase: float = 0.0,
                 dc_offset: float = 0.0,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('amp', ValNumber(0.0), amp)
        self.add_attribute('freq_begin', ValNumber(1e-12), freq_begin)
        self.add_attribute('freq_end', ValNumber(1e-12), freq_end)
        self.add_attribute('phase', ValNumber(), phase)
        self.add_attribute('dc_offset', ValNumber(), dc_offset)

    def __repr__(self) -> str:
        return super().__repr__() + ' {}Hz~{}Hz'.format(
            self.freq_begin(), self.freq_end(),
        )

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            norm = moved / self.duration()
            freqs = np.zeros_like(ts)
            freqs[valids] = norm[valids] * self.freq_end() \
                + (1.0 - norm[valids]) * self.freq_begin()
            phases = np.zeros_like(ts)
            phases[valids] = 2 * np.pi * freqs[valids] * moved[valids] \
                + self.phase()
            ys = np.zeros_like(ts)
            ys[valids] = self.amp() * np.sin(phases[valids]) + self.dc_offset()
            return ys
        else:
            return np.zeros_like(ts)

class ExpoChirpSignal(ChirpSignal):
    """Exponential chirp signal"""

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            norm = moved / self.duration()
            freqs = np.zeros_like(ts)
            log0, log1 = np.log10(self.freq_begin()), np.log10(self.freq_end())
            freqs[valids] = np.power(10.0,
                norm[valids] * log1 + (1.0 - norm[valids]) * log0)
            phases = np.zeros_like(ts)
            phases[valids] = 2 * np.pi * freqs[valids] * moved[valids] \
                + self.phase()
            ys = np.zeros_like(ts)
            ys[valids] = self.amp() * np.sin(phases[valids]) + self.dc_offset()
            return ys
        else:
            return np.zeros_like(ts)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    ts = np.linspace(0.0, 1e-3, 1024, endpoint=False)
    plt.figure(figsize=(15, 12))
    rows, cols, index = 3, 3, 1
    for signal in [
        LinearSignal('linear', 0.2, 0.5),
        SineSignal('sine', 0.75, 1e3, np.pi / 2.0),
        TriangleSignal('triangle', 0.9, 2e3, np.pi / 4.0),
        RampSignal('ramp', 0.8, freq=1.5e3),
        SquareSignal('square', 0.6, freq=4.0e3, phase=np.pi),
        #ChirpSignal('chip1', freq_begin=30e3, freq_end=10e3,
        #            begin=0.1e-3, duration=1e-3),
        ChirpSignal('chip2', amp=0.5, freq_begin=10e3, freq_end=20e3,
                    duration=0.8e-3),
        ExpoChirpSignal('expo_chirp', freq_begin=30e3, freq_end=10e3,
                        begin=0.1e-3, duration=1e-3),
    ]:
        ys = signal(ts)
        plt.subplot(rows, cols, index)
        index += 1
        plt.title(signal.name)
        plt.plot(ts, ys)
    comp = ComplexSineSignal('complex', freq=2.5e3)
    ys = comp(ts)
    plt.subplot(rows, cols, index)
    index += 1
    plt.title('real')
    plt.plot(ts, np.real(ys))
    plt.subplot(rows, cols, index)
    index += 1
    plt.title('imag')
    plt.plot(ts, np.imag(ys))
    plt.show()
