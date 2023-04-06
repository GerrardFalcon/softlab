"""Interface of objects interacting with notebook widgets"""

from abc import abstractmethod
from typing import (
    Optional,
)
from ipywidgets import (
    Output,
    Widget,
)

class Interactive():
    """
    Interface of notebook interactive object
    
    Supported interactive ways:
    - text_output --- property, output widget to print text
    - plot_output --- property, output widget to plot data
    - build_ctrl_widget --- method, construct widget to input and control,
                            should be implemented in derived classes
    - build_result_widget --- method, construct widget to show results,
                              should be implemented in derived classes
    """

    _text_output: Optional[Output] = None
    _plot_output: Optional[Output] = None

    @property
    def text_output(self) -> Optional[Output]:
        """Get output widget to print text"""
        return self._text_output

    @text_output.setter
    def text_output(self, output: Optional[Output]) -> None:
        """Set or remove output widget to print text"""
        if output is not None and not isinstance(output, Output):
            raise TypeError(f'Invalid output widget {type(output)}')
        self._text_output = output

    @property
    def plot_output(self) -> Optional[Output]:
        """Get output widget to plot data"""
        return self._plot_output

    @plot_output.setter
    def plot_output(self, output: Optional[Output]) -> None:
        """Set or remove output widget to plot data"""
        if output is not None and not isinstance(output, Output):
            raise TypeError(f'Invalid output widget {type(output)}')
        self._plot_output = output

    @abstractmethod
    def build_ctrl_widget(self) -> Optional[Widget]:
        """Construct widget to input and control, need implementation"""
        return None

    @abstractmethod
    def build_result_widget(self) -> Optional[Widget]:
        """Construct widget to show results, need implementation"""
        return None
