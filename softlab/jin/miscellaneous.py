"""Miscellaneous tools"""

import os
import numpy as np
import pandas as pd
import io
from matplotlib.figure import Figure
import imageio.v3 as iio

class PrintPattern:
    """Color patterns for print in terminal
    
    Use ``join`` class method to combine patterns
    """

    style_reset = '00'
    style_highlight = '01'
    style_disable = '02'
    style_underline = '04'
    style_flash = '05'
    style_reverse = '07'
    style_invisible = '08'
    style_strikethrough = '09'

    black = '30'
    red = '31'
    green = '32'
    orange = '33'
    blue = '34'
    purple = '35'
    cyan = '36'
    white = '37'
    darkgrey = '90'
    lightred = '91'
    lightgreen = '92'
    yellow = '93'
    lightblue = '94'
    pink = '95'
    lightcyan = '96'

    backgroud_black = '40'
    backgroud_red = '41'
    backgroud_green = '42'
    backgroud_orange = '43'
    backgroud_blue = '44'
    backgroud_purple = '45'
    backgroud_cyan = '46'
    backgroud_white = '47'

    @classmethod
    def join(cls, *args) -> str:
        patterns = list(filter(
            lambda str: len(str) > 0,
            map(lambda arg: str(arg), args),
        ))
        return ';'.join(patterns)

def print_progress(progress: float,
                   pattern: str = PrintPattern.backgroud_green,
                   placeholder: str = ' ',
                   spare_pattern: str = PrintPattern.backgroud_white,
                   spare_holder: str = ' ',
                   bar_length: int = 50,
                   line_length: int = 100,
                   prefix: str = '',
                   suffix: str = '',
                   new_line: bool = False) -> None:
    """
    Print a line as '{prefix}{occupied} {progress}%{suffix}' without feed
    to display progress info in a terminal

    Args:
    - progress --- float number in [0, 1]
    - pattern --- display pattern of occupied area, default is green background
    - placeholder --- char displayed in occupied area
    - spare_pattern --- display pattern of spare area
    - spare_holder --- char displayed in spare area
    - bar_length --- length of progress bar
    - line_length --- minimal length of line
    - prefix --- string displayed at the beginning
    - suffix --- string displayed at the end
    - new_line --- whether to start a new line
    """
    progress = float(progress)
    if progress < 0.0:
        progress = 0.0
    elif progress > 1.0:
        progress = 1.0
    placeholder = str(placeholder)
    if len(placeholder) != 1:
        placeholder = ' '
    bar_length = int(bar_length)
    if bar_length <= 0:
        bar_length = 50
    occupied = placeholder * int(progress * bar_length)
    spare_holder = str(spare_holder)
    if len(spare_holder) != 1:
        spare_holder = ' '
    spared = spare_holder * (bar_length - len(occupied))
    message = f'{prefix}\033[{pattern}m{occupied}\033[0m' \
              f'\033[{spare_pattern}m{spared}\033[0m' \
              f'{int(progress*100):3d}%{suffix}'
    if isinstance(line_length, int) and line_length > len(message):
        message = message + ' ' * (line_length - len(message))
    print(message, end='\n' if new_line else '\r')

def figure_to_array(figure: Figure, **kwargs) -> np.ndarray:
    """Convert matplot figure to NDArray"""
    buffer = io.BytesIO()
    figure.savefig(buffer, format='png', **kwargs)
    return iio.imread(buffer, index=None)

def match_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> bool:
    """Compare columns of ``df1`` and ``df2``, returns True if them match"""
    if isinstance(df1, pd.DataFrame) and isinstance(df2, pd.DataFrame):
        col1 = df1.columns
        col2 = df2.columns
        if len(col1) == len(col2):
            return not (col1.sort_values() != col2.sort_values()).any()
    return False

if __name__ == '__main__':
    import time
    print('Test on progress')
    for i in range(100):
        time.sleep(0.05)
        print_progress((i+1)*0.01, prefix='Progress: ')
    print_progress(1.0, prefix='Progress: ', new_line=True)
    for i in range(100):
        time.sleep(0.05)
        print_progress((i+1)*0.01, placeholder='#', 
                       pattern=PrintPattern.join(PrintPattern.style_highlight, 
                                                 PrintPattern.yellow),
                       spare_holder='=', spare_pattern='',
                       suffix=f' [{i*0.05:.2f}s]')
    print_progress(1.0, pattern='33', placeholder='#', 
                   suffix=' [5.00s]', new_line=True)

    import matplotlib.pyplot as plt
    print('Try convert figure to ndarray')
    fig = plt.figure(figsize=(3, 2))
    plt.plot(np.linspace(0, 10, 11), np.linspace(0, 20, 11))
    array = figure_to_array(fig)
    print(f'Shape of ndarray of figure: {array.shape}')
    array = figure_to_array(fig, dpi=360)
    print(f'Shape changes to {array.shape} with dpi 360')

    print('Compare dataframes')
    df1 = pd.DataFrame({'a': [0, 1], 'b': [2, 3]})
    df2 = pd.DataFrame(columns=['b', 'a'])
    df3 = pd.DataFrame(columns=['c', 'b', 'a'])
    df4 = pd.DataFrame({'a': [0, 1], 'c': [2, 3]})
    for a, b in [(df1, df2), (df1, df3), (df1, df4)]:
        print(f'{a.columns}, {b.columns}: {match_dataframes(a, b)}')
