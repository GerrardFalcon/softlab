"""Noise signals"""

from typing import Optional
import numpy as np
from softlab.jin import ValNumber
from softlab.tu.dsp.base import Signal
from softlab.tu.dsp.operate import (
    unbias,
    normalize,
)

class Noise(Signal):
    """
    Abstract class of any noises

    Arguments:
    - amp -- maximum amplitude of window, default is 1.0, is also an attribute
    """

    def __init__(self, name: Optional[str] = None,
                 amp: float = 1.0) -> None:
        super().__init__(name)
        self.add_attribute('amp', ValNumber(0.0), amp)

    def __repr__(self) -> str:
        return super().__repr__() + f' Amp {self.amp()}'

class UniformNoise(Noise):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        return np.random.uniform(-self.amp(), self.amp(), ts.shape)

class BrownianNoise(Noise):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        dys = np.random.uniform(-1, 1, ts.shape)
        ys = np.cumsum(dys)
        return normalize(unbias(ys), self.amp())

class GaussianNoise(Noise):

    def evaluate(self, ts: np.ndarray) -> np.ndarray:
        return np.random.normal(0.0, self.amp(), ts.shape)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    rows, cols, index = 1, 3, 1
    plt.figure(figsize=(cols*5, rows*3.5))
    ts = np.linspace(0.0, 1.0, 128, endpoint=False)
    for signal in [
        UniformNoise('uniform', 0.75),
        BrownianNoise('brownian', 2.0),
        GaussianNoise('gauss', 0.1),
    ]:
        ys = signal(ts)
        plt.subplot(rows, cols, index)
        index += 1
        plt.title(signal.name)
        plt.plot(ts, ys)
    plt.show()
