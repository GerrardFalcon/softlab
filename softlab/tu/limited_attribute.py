"""Attribute bound by given validator"""
from typing import Any
from softlab.jin import Validator

class LimitedAttribute:
    """
    An attribute with validator

    Args:
        - vals, the validator of attribute
        - initial_value, the initial value of attribute
    """
    def __init__(self, vals: Validator, initial_value: Any) -> None:
        self._vals = vals
        self._value = None
        self.set(initial_value)

    def set(self, value: Any) -> None:
        """Set attribute value, should follows the validator"""
        self._vals.validate(value)
        self._value = value
    
    def get(self) -> Any:
        """Get attribute value"""
        return self._value

    def __call__(self, *args: Any) -> Any:
        """Get or set attribute value, makes attribute callable"""
        if len(args) == 0:
            return self.get() # get value
        else:
            self.set(args[0]) # set value
