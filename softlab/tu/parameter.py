"""Parameter interface"""

from abc import abstractmethod
from typing import (
    Any,
    Optional,
)
import warnings
from softlab.jin import (
    Validator,
    ValNumber,
)
import math

class Parameter():
    """
    Parameter base class

    A parameter represents a single degree of freedom, it can be an attribute
    of a device, a specific measurement or a result of an analysis task.

    There are 5 properties:
        name --- non-empty string representing the parameter
        validator --- description of the validator that guards the input of 
                      parameter, read-only
        settable --- whether the parameter can be set, read-only
        gettable --- whether the parameter can be get, read-only
        owner --- the owner object of parameter, e.g. a device or a task

    public methods:
        snapshot() -> dict --- returns the snapshot dict of parameter
        set(value: Any) --- set parameter value
        get() -> Any --- get parameter value

    Abstract methods that should be implemented in derived classes:
        parse(value: Any) -> Any --- parse the input value, used in ``set``
        before_set(currennt: Any, next: Any) --- hook function before setting,
                                                 used in ``set``
        after_set(value: Any) --- hook function after setting, used in ``set``
        before_get(value: Any) --- hook function before getting, used in ``get``
        interprete(value: Any) -> Any --- interprete value, used in ``get``
    """

    def __init__(self,
                 name: str,
                 validator: Validator = ValAnything,
                 settable: bool = True,
                 gettable: bool = True,
                 init_value: Optional[Any] = None,
                 owner: Optional[Any] = None) -> None:
        """
        Initialize parameter

        Args:
            name --- parameter name, non-empty string
            validator --- validator for inner value, ``Validator`` instance
            settable --- whether the parameter can be set
            gettable --- whether the parameter can be get
            init_value --- initial value, optional
            owner --- parameter owner, optional

        Note: warning if settable and gettable are both False
        """
        self._name = str(name) # parameter name
        if len(self._name) == 0:
            raise ValueError('Given name is empty')
        if not isinstance(validator, Validator): # validator
            raise TypeError(f'Invalid validator {type(validator)} for {name}')
        self._validator = validator
        self._settable = settable if isinstance(settable, bool) else True # access
        self._gettable = gettable if isinstance(gettable, bool) else True
        if not self._settable and not self._gettable:
            warnings.warn(
                f'Parameter {self.name} is neither settable and gettable')
        self._value: Any = None # initial value
        if init_value is not None:
            if self.settable:
                self.set(init_value)
            else:
                self._validator.validate(init_value)
                self._value = init_value
        self.owner = owner # owner

    @property
    def name(self) -> str:
        """Get parameter name"""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """Set parameter name"""
        name = str(name)
        if len(name) > 0:
            self._name = name
        else:
            raise ValueError(f'New name is empty (current name: {self._name})')

    @property
    def validator(self) -> str:
        """Get description of validator"""
        return repr(self._validator)

    @property
    def settable(self) -> bool:
        """Get whether the paremter can be set"""
        return self._settable

    @property
    def gettable(self) -> bool:
        """Get whether the paremter can be get"""
        return self._gettable

    def __repr__(self) -> str:
        return f'{type(self)}/{self.name}'

    def snapshot(self) -> dict:
        """Get parameter snapshot"""
        return {
            'name': self.name,
            'type': type(self),
            'settable': self.settable,
            'gettable': self.gettable,
            'validator': self.validator,
            'owner': str(self.owner),
        }

    def set(self, value: Any) -> None:
        """Set parameter value"""
        if not self.settable:
            raise RuntimeError(f'Parameter {self.name} is not settable')
        self._validator.validate(value, repr(self))
        value = self.parse(value)
        self.before_set(self._value, value)
        self._value = value
        self.after_set(self._value)

    def get(self) -> Any:
        """Get parameter value"""
        if not self.gettable:
            raise RuntimeError(f'Parameter {self.name} is not gettable')
        self._value = self.before_get(self._value)
        return self.interprete(self._value)

    def __call__(self, *args: Any) -> Any:
        """Get or set parameter value, makes parameter callable"""
        if len(args) == 0:
            return self.get() # get value
        else:
            self.set(args[0]) # set value

    @abstractmethod
    def parse(self, value: Any) -> Any:
        """
        Parse value at the beginning of ``set``, implemented in derived class

        Args:
            value --- the input of setting

        Returns:
            the parsed result for inner value
        """
        return value

    @abstractmethod
    def before_set(self, current: Any, next: Any) -> None:
        """
        Hook function before setting of value, implemented in derived class

        Args:
            current --- current value of parameter
            next --- the value prepared to be set
        """
        pass

    @abstractmethod
    def after_set(self, value: Any) -> None:
        """
        Hook function after setting of value, implemented in derived class

        Args:
            value --- new value of parameter
        """
        pass

    @abstractmethod
    def before_get(self, value: Any) -> Any:
        """
        Hook function before getting of value, implemented in derived class

        Args:
            value --- the inner value when ``get`` is called

        Returns:
            post manipulation value
        """
        return value

    @abstractmethod
    def interprete(self, value: Any) -> Any:
        """
        Interprete inner value for getting, implemented in derived class

        Args:
            value --- inner value

        Returns:
            the interpreted value for caller of ``get``
        """
        return value
    
class QuantizedParameter(Parameter):
    """
    Parameter with quantized inner data

    Additional properties:
        lsb --- least sigificant bit, aka the step of quantization
        mode --- quantization mode, round, floor or ceil
    """

    def __init__(self, name: str,
                 settable: bool = True, gettable: bool = True,
                 min: float = 0.0, max: float = 100.0, lsb: float = 1.0,
                 mode: str = 'round',
                 init_value: Optional[float] = None,
                 owner: Optional[Any] = None) -> None:
        """
        Initialization

        Arguments not in super initialization:
            min --- minimal value
            max --- maximal value
            lsb --- least sigificant bit
            mode --- quantization mode, round, floor or ceil
        """
        super().__init__(name, ValNumber(min, max),
                         settable, gettable, init_value, owner)
        if not isinstance(min, float) or not isinstance(max, float) or \
                not isinstance(lsb, float):
            raise TypeError(
                f'Invalid type: {type(min)}, {type(max)}, {type(lsb)}')
        if lsb > 0 and max > min and (max-min) > lsb:
            self._lsb = lsb
        else:
            raise ValueError(f'Invalid value: {min}, {max}, {lsb}')
        self._quantizer = round
        if mode == 'floor':
            self._quantizer = math.floor
        elif mode == 'ceil':
            self._quantizer = math.ceil

    @property
    def lsb(self) -> float:
        """Get least sigificant bit"""
        return self._lsb
    
    @property
    def mode(self) -> str:
        """Get quantization mode"""
        if self._quantizer == math.floor:
            return 'floor'
        elif self._quantizer == math.ceil:
            return 'ceil'
        return 'round'
    
    def snapshot(self) -> dict:
        s = super().snapshot()
        s['lsb'] = self.lsb
        s['mode'] = self.mode
        return s

    def parse(self, value: float) -> int:
        return self._quantizer(value / self._lsb)
    
    def interprete(self, value: int) -> float:
        return self._lsb * value
    
if __name__ == '__main__':
    from softlab.jin import (
        ValType,
        ValInt,
        ValAnything,
        ValNothing,
        ValPattern,
    )
    for para, val in [
        (Parameter('demo', ValAnything(), init_value=42), 'lab'),
        (Parameter('email1', ValPattern('\w+(\.\w+)*@\w+(\.\w+)+')), 'a@b.com'),
        (Parameter('email2', ValPattern('\w+(\.\w+)*@\w+(\.\w+)+')), 'a_b.com'),
        (Parameter('int', ValInt(0, 100), settable=False, init_value=61), 73),
        (Parameter('percentage', ValInt(0, 100), gettable=False), 73),
        (Parameter('noaccess', ValNothing('test'), False, False), 0),
        (Parameter('bool', ValType(bool), owner='pk'), False),
        (QuantizedParameter('adc', False, lsb=100.0/256, init_value=18), 13.2),
        (QuantizedParameter('dac', gettable=False, lsb=150.0/65536), 89.2),
        (QuantizedParameter('quantizer', min=-20.0, max=20.0, lsb=40.0/65536, owner='pk'), -10.328977345),
    ]:
        print(f'-------- {para} --------')
        print(para.snapshot())
        print(f'Try set value: {val}')
        try:
            para(val)
        except Exception as e:
            print(e)
        try:
            print(f'Try get value: {para()}')
        except Exception as e:
            print(e)
