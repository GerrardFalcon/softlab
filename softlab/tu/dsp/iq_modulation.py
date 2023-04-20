"""Functions about IQ modulation and demodulation"""

from typing import (
    Optional,
    Tuple,
    Union,
    Callable,
)
import numpy as np
from softlab.tu.dsp.base import (
    Signal,
    Wavement,
)
from softlab.tu.dsp.common import SineSignal

def generate_iq_wavements(
        t: np.ndarray, fc: float,
        out_envelope: Union[np.ndarray, Signal],
        out_phi: Union[np.ndarray, Signal]) -> Tuple[Wavement, Wavement]:
    """
    Generate IQ wavements

    Args:
        - t, time sequence, unit: s
        - fc, carrier frenquency, unit: Hz
        - out_envelope, envelope of output signal, can be value array or signal
        - out_phi, angle of output signal, can be value array or signal

    Return:
        tuple of I and Q channel wavements

    Note that the form of output signal is ``out_envelope * cos(out_phi)``
    """
    if not isinstance(t, np.ndarray):
        raise TypeError(f'Invalid time sequence {type(t)}')
    shape_t = t.shape
    if len(shape_t) > 1 or shape_t[0] == 0:
        raise ValueError(f'Invalid time sequence shape {shape_t}')
    fc = float(fc)
    if fc < 1e-3:
        raise ValueError(f'Invalid carrier frenquecy {fc}')
    if isinstance(out_envelope, Signal):
        out_envelope = out_envelope(t)
    if not isinstance(out_envelope, np.ndarray) or out_envelope.shape != shape_t:
        raise ValueError(f'Invalid output envelop {out_envelope}')
    if isinstance(out_phi, Signal):
        out_phi = out_phi(t)
    if not isinstance(out_phi, np.ndarray) or out_phi.shape != shape_t:
        raise ValueError(f'Invalid output phi')
    theta = out_phi - 2.0 * np.pi * fc * t
    return Wavement(t, out_envelope * np.cos(theta)), \
           Wavement(t, out_envelope * np.sin(theta))

def iq_modulation(fc: float, I: Wavement, Q: Wavement) -> Wavement:
    """
    Perform IQ modulation in digital

    Args:
        - fc, carrier frenquency, unit: Hz
        - I, wavement of I channel
        - Q, wavement of Q channel

    Return: wavement after modulation
    """
    if not isinstance(I, Wavement) or not isinstance(Q, Wavement):
        raise TypeError(f'Invalid I/Q wavements {type(I)}, {type(Q)}')
    if len(I) == 0 or len(I) != len(Q):
        raise ValueError(f'Invalid wavement lengths {len(I)}, {len(Q)}')
    fc = float(fc)
    if fc < 1e-3:
        raise ValueError(f'Invalid carrier frenquecy {fc}')
    carrier_i, carrier_q = SineSignal(freq=fc), \
                           SineSignal(freq=fc, phase=-np.pi/2)
    return Wavement(
        I.times, I.window(carrier_i).values - Q.window(carrier_q).values)

def iq_demodulation(
        w: Wavement, fc: float,
        filter: Optional[Callable] = None) -> Tuple[Wavement, Wavement]:
    """
    Perform IQ demodulation in digital

    Args:
        - w, input wavement to demodulate
        - fc, carrier frequency, unit: Hz
        - filter, filter after demodulation, optional

    Return: tuple of wavements of I and Q channels
    """
    if not isinstance(w, Wavement):
        raise TypeError(f'Invalid wavement {type(w)}')
    if len(w) == 0:
        raise ValueError(f'Empty wavement')
    fc = float(fc)
    if fc < 1e-3:
        raise ValueError(f'Invalid carrier frenquecy {fc}')
    carrier_i, carrier_q = SineSignal(freq=fc), \
        SineSignal(freq=fc, phase=np.pi/2)
    I = w.window(carrier_i)
    Q = w.window(carrier_q)
    if isinstance(filter, Callable):
        return (filter(I), filter(Q))
    return (I, Q)

if __name__ == '__main__':
    from softlab.tu.dsp.common import LinearSignal
    from softlab.tu.dsp.window import RectangleWindow
    import scipy as sp
    import matplotlib.pyplot as plt
    fc, fm, ff = 5e9, 100e6, 1e9
    sample_rate = 1e12
    T, begin, end = 100e-9, 10e-9, 90e-9
    points = int(T * sample_rate) + 1
    win = RectangleWindow(begin=begin, duration=end-begin)
    ts = np.linspace(0.0, T, points)
    out_i, out_q = generate_iq_wavements(
        ts, fc, win, LinearSignal(coeff=2.0*np.pi*(fc+fm)))
    out = iq_modulation(fc, out_i, out_q)
    def lp_filter(w: Wavement) -> Wavement:
        b, a = sp.signal.butter(4, ff * 2.0 / sample_rate)
        zi = sp.signal.lfilter_zi(b, a)
        return Wavement(w.times,
                        sp.signal.lfilter(b, a, w.values, zi=zi*w.values[0])[0])
    in_i, in_q = iq_demodulation(out, fc, lp_filter)
    plt.figure(figsize=(10, 6))
    plt.subplot(221)
    plt.plot(ts, win(ts))
    plt.subplot(222)
    plt.plot(ts, out.values)
    plt.subplot(223)
    plt.plot(ts, out_i.values, label='Iout')
    plt.plot(ts, out_q.values, label='Qout')
    plt.legend()
    plt.subplot(224)
    plt.plot(ts, in_i.values, label='Iin')
    plt.plot(ts, in_q.values, label='Qin')
    plt.legend()
    plt.show()
