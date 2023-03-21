"""
Common process of signals and wavements
"""
from typing import Any
import numpy as np
from softlab.tu.dsp.base import (
    Signal,
    Wavement,
)

def unbias(seq: np.ndarray) -> np.ndarray:
    """Remove bias of any sequence"""
    if not isinstance(seq, np.ndarray):
        raise TypeError(f'Invalid sequence type: {type(seq)}')
    return seq - np.mean(seq)

def normalize(seq: np.ndarray, max: float = 1.0) -> np.ndarray:
    """Normalize any sequence into [-``max``, ``max``] interval"""
    if not isinstance(seq, np.ndarray):
        raise TypeError(f'Invalid sequence type: {type(seq)}')
    if not isinstance(max, float):
        raise TypeError(f'Invalid max type: {type(max)}')
    if max > 0.0:
        amp = np.max([np.abs(np.min(seq)), np.abs(np.max(seq))])
        if amp > 0.0:
            return seq * (max / amp)
    return np.zeros_like(seq)

def pad(seq: np.ndarray, 
        before: int = 0, after: int = 0,
        fill: Any = 0.0) -> np.ndarray:
    """
    Pad sequence with given value

    Arguments:
    - seq -- the sequence to pad
    - before -- pad count before the sequence
    - after -- pad count after the sequence
    - fill -- padding value
    """
    if not isinstance(seq, np.ndarray):
        raise TypeError(f'Invalid sequence type: {type(seq)}')
    if not isinstance(before, int) or before < 0:
        before = 0
    if not isinstance(after, int) or after < 0:
        after = 0
    if before + after == 0:
        return seq
    i_len = seq.size
    o_len = i_len + before + after
    i_shape = seq.shape
    if len(i_shape) == 1:
        o_shape = (o_len,)
    elif len(i_shape) == 2:
        if i_shape[0] == 1:
            o_shape = (1, o_len)
        elif i_shape[1] == 1:
            o_shape = (o_len, 1)
        else:
            raise ValueError(f'Invalid input shape {i_shape}')
    else:
        raise ValueError(f'Invalid input shape {i_shape}')
    i_seq = seq.reshape((i_len,))
    o_seq = np.full((o_len,), fill, seq.dtype)
    o_seq[before:(before+i_len)] = i_seq
    return o_seq.reshape(o_shape)

def sample_signal(sig: Signal,
                  begin: float, end: float, count: int) -> Wavement:
    """
    Generate a wavement by sampling a signal

    Arguments:
    - sig -- signal to sample
    - begin -- beginning of sampling
    - end -- end of sampling
    - count -- sample point count
    """
    if not isinstance(sig, Signal):
        raise TypeError(f'Invalid type of signal: {type(sig)}')
    ts = np.linspace(begin, end, count)
    ys = sig.evaluate(ts)
    return Wavement(ts, ys)

if __name__ == '__main__':
    from softlab.tu.dsp.common import SineSignal, FixedSignal
    print('Test sampling')
    wave = sample_signal(SineSignal(freq=50.0), 0.0, 1.0, 1001)
    assert(len(wave) == 1001)
    print(f'Length {len(wave)}, offset {wave.offset}, '
          f'duration {wave.duration}, end {wave.end}')
    print(f'10th item: {wave[9]}, 578th item: {wave[577]}')
    wave = wave.delay(0.7).scale(10.0) \
               .stretch(2.0, True).window(FixedSignal(0.7)) \
               .quantize(0.1)
    print('After munipulation')
    print(f'Length {len(wave)}, offset {wave.offset}, '
          f'duration {wave.duration}, end {wave.end}')
    print(f'10th item: {wave[9]}, 578th item: {wave[577]}')
    print()
    print('Test padding')
    seq = wave.values
    padded = pad(seq, after=5)
    print(f'{seq.shape} -> {padded.shape}, {padded[0]} {padded[-1]}')
    padded = pad(seq, before=2, after=-1, fill=-np.inf)
    print(f'{seq.shape} -> {padded.shape}, {padded[0]} {padded[-1]}')
    seq = seq.reshape((1, seq.size))
    padded = pad(seq, after=5)
    print(f'{seq.shape} -> {padded.shape}, {padded[0][0]} {padded[0][-1]}')
    padded = pad(seq, before=2, after=-1, fill=-np.inf)
    print(f'{seq.shape} -> {padded.shape}, {padded[0][0]} {padded[0][-1]}')
    print()
