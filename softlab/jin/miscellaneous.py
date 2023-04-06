"""Miscellaneous tools"""

import os
import numpy as np
import io
from matplotlib.figure import Figure
import imageio.v3 as iio
from softlab.shui.data import (
    DataGroup,
    DataRecord,
    DataChart,
)

def print_progress(progress: float,
                   pattern: str = '42',
                   placeholder: str = ' ',
                   length: int = 50,
                   prefix: str = '',
                   suffix: str = '') -> None:
    """
    Print a line as '{prefix}{occupied} {progress}%{suffix}' without feed
    to display progress info in a terminal

    Args:
    - progress --- float number in [0, 1]
    - pattern --- display pattern of occupied area, default is green background
    - placeholder --- string displayed in every unit of occupied area
    - length --- total count of occupied area,
                 actual text length is len(placeholder) * length
    - prefix --- string displayed at the beginning
    - suffix --- string displayed at the end
    """
    progress = float(progress)
    if progress < 0.0:
        progress = 0.0
    elif progress > 1.0:
        progress = 1.0
    placeholder = str(placeholder)
    if len(placeholder) == 0:
        placeholder = ' '
    length = int(length)
    if length <= 0:
        length = 50
    occupied = placeholder * int(progress * length)
    print(f'\r{prefix}\033[{pattern}m{occupied}\033[0m '
          f'{int(progress*100)}%{suffix}', end='')

def figure_to_array(figure: Figure, **kwargs) -> np.ndarray:
    buffer = io.BytesIO()
    figure.savefig(buffer, format='png', **kwargs)
    return iio.imread(buffer, index=None)

def extract_group_to_folder(group: DataGroup, folder: str) -> tuple[int, int]:
    if not isinstance(group, DataGroup):
        raise TypeError(f'Invalid data group {type(group)}')
    folder = str(folder)
    os.makedirs(folder, exist_ok=True)
    record_count = 0
    chart_count = 0
    for r_name in group.records:
        record = group.record(r_name)
        if isinstance(record, DataRecord):
            record.table.to_csv(os.path.join(
                folder, f'{record.name}.csv',
            ), seq=', ', index=False)
            for c_name in record.charts:
                chart = record.chart(c_name)
                if isinstance(chart, DataChart):
                    chart.write(os.path.join(
                        folder, f'{record.name}.{chart.title}.png',
                    ))
                    chart_count = chart_count + 1
    return (record_count, chart_count)

if __name__ == '__main__':
    import time
    print('Test on progress')
    for i in range(100):
        time.sleep(0.05)
        print_progress((i+1)*0.01, prefix='Progress: ')
    print()
    for i in range(100):
        time.sleep(0.05)
        print_progress((i+1)*0.01, pattern='33', placeholder='#', 
                       suffix=f' [{i*0.1:.1f}s]')
    print()

    import matplotlib.pyplot as plt
    print('Try convert figure to ndarray')
    fig = plt.figure(figsize=(3, 2))
    plt.plot(np.linspace(0, 10, 11), np.linspace(0, 20, 11))
    array = figure_to_array(fig)
    print(f'Shape of ndarray of figure: {array.shape}')
    array = figure_to_array(fig, dpi=360)
    print(f'Shape changes to {array.shape} with dpi 360')
