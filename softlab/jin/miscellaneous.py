"""Miscellaneous tools"""

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

if __name__ == '__main__':
    import time
    print('Test on progress')
    for i in range(100):
        time.sleep(0.05)
        print_progress((i+1)*0.01, prefix='Progress: ')
    print()
    for i in range(100):
        time.sleep(0.1)
        print_progress((i+1)*0.01, pattern='33', placeholder='#', 
                       suffix=f' [{i*0.1:.1f}s]')
    print()
