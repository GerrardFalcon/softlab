"""
Signal related module

Public attributes:

| name              | type     | description                                  |
| ----------------- | -------- | -------------------------------------------- |
| Signal            | class    | Abstract class representing a signal         |
| Wavement          | class    | A pair of a time sequence and value sequece  |
| FactorSignal      | class    | Any signal multiplied by a factor            |
| OffsetSignal      | class    | Any signal plus an offset                    |
| SumSignal         | class    | Sum of several signals                       |
| ConcatSignal      | class    | Concatenation of several signals             |
| ReciprocalSignal  | class    | Fraction of a factor above a signal          |
| FunctionalSignal  | class    | A signal defined by a given function         |
| FixedSignal       | class    | A signal with fixed value                    |
| PeriodicSignal    | class    | Abstract class of any periodical signal      |
| SineSignal        | class    | A sine signal with real number               |
| ComplexSineSignal | class    | A sine signal with complex number            |
| TriangleSignal    | class    | Periodic triangle signal                     |
| RampSignal        | class    | Periodic ramp signal                         |
| SquareSignal      | class    | Periodic square signal                       |
| PulseSignal       | class    | Abstract class of any pulse-like signal      |
| ChirpSignal       | class    | Linear chirp signal                          |
| ExpoChirpSignal   | class    | Exponential chirp signal                     |
| Window            | class    | Abstract class of any window                 |
| RectangleWindow   | class    | Rectangle window                             |
| CosineWindow      | class    | Cosine window                                |
| GaussianWindow    | class    | Gaussian window                              |
| HanningWindow     | class    | Hanning window                               |
| HammingWindow     | class    | Hamming window                               |
| TriangleWindow    | class    | Triangle window                              |
| ChebyshevWindow   | class    | Chebyshev window                             |
| BlackmanWindow    | class    | Blackman window                              |
| SlepianWindow     | class    | Slepian window (general gaussian window)     |
| Noise             | class    | Abstract class of any noise                  |
| UniformNoise      | class    | Uncorrected uniform noise                    |
| BrownianNoise     | class    | Brownian noise                               |
| GaussianNoise     | class    | Uncorrected gaussian noise                   |
| unbias            | function | Remove bias of any sequence                  |
| normalize         | function | Normalize sequence into [-max, max] interval |
| pad               | function | Pad a sequence with given value              |
| sample_signal     | function | Generate a wavement by sampling a signal     |
"""

from softlab.tu.dsp.base import (
    Signal,
    Wavement,
    FactorSignal,
    OffsetSignal,
    SumSignal,
    ConcatSignal,
    ReciprocalSignal,
)

from softlab.tu.dsp.common import (
    FunctionalSignal,
    FixedSignal,
    PeriodicSignal,
    SineSignal,
    ComplexSineSignal,
    TriangleSignal,
    RampSignal,
    SquareSignal,
    PulseSignal,
    ChirpSignal,
    ExpoChirpSignal,
)

from softlab.tu.dsp.window import (
    Window,
    RectangleWindow,
    CosineWindow,
    GaussianWindow,
    HanningWindow,
    HammingWindow,
    TriangleWindow,
    ChebyshevWindow,
    BlackmanWindow,
    SlepianWindow,
)

from softlab.tu.dsp.noise import (
    Noise,
    UniformNoise,
    BrownianNoise,
    GaussianNoise,
)

from softlab.tu.dsp.operate import (
    unbias,
    normalize,
    pad,
    sample_signal,
)
