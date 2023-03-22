"""
Window signals
"""
from typing import (
    Any,
    Optional,
)
import numpy as np
from scipy.signal.windows import dpss
from softlab.jin import (
    ValNumber,
    ValInt,
)
from softlab.tu.dsp.common import PulseSignal
from softlab.tu.dsp.operate import normalize

class Window(PulseSignal):
    """
    Abstract class of any window signals

    Subclass of ``PulseSignal`` with one additional argument:
    - amp -- maximum amplitude of window, default is 1.0

    ``amp`` is also an attribute
    """

    def __init__(self, name: Optional[str] = None,
                 amp: float = 1.0,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('amp', ValNumber(0.0), amp)

    def __repr__(self) -> str:
        return super().__repr__() + f' Amp {self.amp()}'

class RectangleWindow(Window):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        ys = np.zeros_like(ts)
        ys[self.get_valids(ts)] = self.amp()
        return ys
    
class CosineWindow(Window):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        ys = np.zeros_like(ts)
        if self.duration() > 0.0:
            freq = 1.0 / (2.0 * self.duration())
            ys[self.get_valids(ts)] = self.amp() * np.sin(2.0 * np.pi * freq * \
                (ts[self.get_valids(ts)] - self.begin()))
        return ys

class GaussianWindow(Window):
    """
    Gaussian window

    Subclass of ``Window`` with one additional argument:
    - sigma -- standard error, positive value, default 1.0, attribute

    There is another property ``shape_factor``, related to duration and sigma:
        shape_factor = duration / (2 sigma)
    """

    def __init__(self, name: Optional[str] = None,
                 sigma: float = 1.0,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('sigma', ValNumber(1e-18), sigma)

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            ys[valids] = self.amp() * np.exp(
                - ((moved[valids] - self.duration()*0.5)**2) \
                / (2.0 * self.sigma() * self.sigma())
            )
        return ys

    @property
    def shape_factor(self) -> float:
        return self.duration() / 2.0 / self.sigma()

    @shape_factor.setter
    def shape_factor(self, val: float) -> None:
        self.sigma(self.duration() / 2.0 / val)

class HanningWindow(Window):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            ys[valids] = self.amp() * 0.5 * (1.0 - np.cos(
                2.0 * np.pi * moved[valids] / self.duration()
            )) 
        return ys

class HammingWindow(Window):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            ys[valids] = self.amp() * (0.54 -  0.46 * np.cos(
                2.0 * np.pi * moved[valids] / self.duration()
            )) 
        return ys

class TriangleWindow(Window):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            ys[valids] = self.amp() * (1.0 - np.abs(
                2.0 * moved[valids] / self.duration() - 1.0
            )) 
        return ys

class ChebyshevWindow(Window):
    """
    Chebyshev window

    Subclass of ``Window`` with one additional argument:
    - sidelobe -- sidelobe restrain level, default 100dB, attribute
    """

    def __init__(self, name: Optional[str] = None,
                 sidelobe: float = 100.0,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('sidelobe', ValNumber(0.0), sidelobe)
        self._win: Optional[np.ndarray] = None
        self._sidelobe = self.sidelobe()

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            t = self.duration()
            if (ts[1] - ts[0]) > 0.0:
                M = round(t / (ts[1] - ts[0]))
                if M >= 2:
                    step = t / M
                    win = self._get_win(M)
                    indexes = np.floor((ts-self.begin()) / step).astype('int32')
                    indexes[indexes>=M] = M-1
                    ys[valids] = win[indexes[valids]] * self.amp()
        return ys

    def _get_win(self, M: int) -> np.ndarray:
        if isinstance(self._win, np.ndarray) and len(self._win) == M \
                and np.abs(self._sidelobe - self.sidelobe()) < 1e-6:
            return self._win
        self._sidelobe = self.sidelobe()
        ratio = np.power(10.0, self._sidelobe / 20.0)
        beta = np.cosh(np.arccosh(ratio) / (M-1))
        ks = np.arange(float(M))
        #print(f'{M} {ratio} {beta}')
        Am = beta * np.cos(np.pi * ks / M)
        Am_abs = np.abs(Am)
        omega = np.zeros_like(ks)
        omega[Am_abs<=1.0] = np.cos(M * np.arccos(Am[Am_abs<=1.0]))
        omega[Am_abs>1.0] = np.cosh(M * np.arccosh(Am_abs[Am_abs>1.0]))
        omega = omega * np.power(-1.0, ks)
        seq = np.real(np.fft.ifft(omega))
        seq[0] = seq[-1]
        self._win = normalize(seq)
        assert(len(self._win) == M)
        return self._win

class BlackmanWindow(Window):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            moved = ts - self.begin()
            ys[valids] = self.amp() * (0.42 - 0.5 * np.cos(
                2.0 * np.pi * moved[valids] / self.duration()
            ) + 0.08 * np.cos(
                4.0 * np.pi * moved[valids] / self.duration()
            ))
        return ys
    
class SlepianWindow(Window):

    def __init__(self, name: Optional[str] = None,
                 alpha: float = 1.0, order: int = 0,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(name, *args, **kwargs)
        self.add_attribute('alpha', ValNumber(1e-12), alpha)
        self.add_attribute('order', ValInt(0), order)
        self._win: Optional[np.ndarray] = None
        self._alpha = self.alpha()
        self._order = self.order()

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        valids = self.get_valids(ts)
        ys = np.zeros_like(ts)
        if np.sum(valids) > 0:
            t = self.duration()
            if (ts[1] - ts[0]) > 0.0:
                M = round(t / (ts[1] - ts[0]))
                if M >= 2:
                    step = t / M
                    win = self._get_win(M)
                    indexes = np.floor((ts-self.begin()) / step).astype('int32')
                    indexes[indexes>=M] = M-1
                    ys[valids] = win[indexes[valids]] * self.amp()
        return ys

    def _get_win(self, M: int) -> np.ndarray:
        if isinstance(self._win, np.ndarray) and len(self._win) == M and \
                np.abs(self._alpha - self.alpha()) < 1e-6 and \
                self._order == self.order():
            return self._win
        self._alpha = self.alpha()
        self._order = self.order()
        win = dpss(M, self._alpha, self._order + 1, norm='approximate')
        self._win = win[self._order, :].T
        assert(len(self._win) == M)
        return self._win

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    rows, cols, index = 3, 3, 1
    plt.figure(figsize=(cols * 5, rows * 3.5))
    kwargs = {'begin': 0.5e-3, 'duration': 1.0e-3}
    ts = np.linspace(0.0, 2.0e-3, 1024, endpoint=False)
    for signal in [
        RectangleWindow('rect', **kwargs),
        CosineWindow('cosine', **kwargs),
        GaussianWindow('gauss1', 0.2e-3, **kwargs),
        #GaussianWindow('gauss2', 0.1e-3, **kwargs),
        HanningWindow('hanning', **kwargs),
        HammingWindow('hamming', **kwargs),
        TriangleWindow('triangle', **kwargs),
        ChebyshevWindow('chebyshev1', 120.0, **kwargs),
        #ChebyshevWindow('chebyshev2', 40.0, **kwargs),
        BlackmanWindow('blackman', **kwargs),
        SlepianWindow('slepian_0', 1.0, **kwargs),
        #SlepianWindow('slepian_3', 2.5, 3, **kwargs),
    ]:
        ys = signal(ts)
        plt.subplot(rows, cols, index)
        index += 1
        plt.title(signal.name)
        plt.plot(ts, ys)
    plt.show()
