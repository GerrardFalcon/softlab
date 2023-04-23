"""Validators for different types of value"""

from typing import (
    Any,
    Sequence,
    Set,
    Union,
    Optional,
)
import numpy as np
import re

class Validator():
    """
    Base class for all validators

    Every validator should implement ``validate`` method,
    which checks value validation and raises error if invalid

    Another implementable method is ``__repr__`` which should return
    specific description of validator
    """

    def validate(self, value: Any, context: str = '') -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{type(self)}'

def validate_value(value: Any, validator: Validator, context: str = '') -> bool:
    """Function to validate value by given validator"""
    try:
        validator.validate(value, context)
    except Exception as e:
        print(e)
        return False
    return True

class ValidatorAll(Validator):
    """
    Validator requires value satisfying all sub validators

    Args:
    - validators --- sequence of sub validators
    """

    def __init__(self, validators: Sequence[Validator]) -> None:
        if not isinstance(validators, Sequence):
            raise TypeError(f'sub validators should be a sequence')
        self._children = tuple(filter(
            lambda v: isinstance(v, Validator), validators
        ))
        if len(self._children) == 0:
            raise ValueError(f'No valid sub validator')

    def validate(self, value: Any, context: str = '') -> None:
        for child in self._children:
            child.validate(value, context)

    def __repr__(self) -> str:
        return super().__repr__() + ' ({})'.format(', '.join(map(
            lambda child: repr(child), self._children
        )))

class ValidatorAny(Validator):
    """
    Validator requires value satisfying at least one sub validators

    Args:
    - validators --- sequence of sub validators
    """

    def __init__(self, validators: Sequence[Validator]) -> None:
        if not isinstance(validators, Sequence):
            raise TypeError(f'sub validators should be a sequence')
        self._children = tuple(filter(
            lambda v: isinstance(v, Validator), validators
        ))
        if len(self._children) == 0:
            raise ValueError(f'No valid sub validator')

    def validate(self, value: Any, context: str = '') -> None:
        succ = False
        for child in self._children:
            try:
                child.validate(value, context)
            except Exception:
                continue
            succ = True
            break
        if not succ:
            raise ValueError(
                f'{value} is not accepted by any validators in {context}')

    def __repr__(self) -> str:
        return super().__repr__() + ' ({})'.format(', '.join(map(
            lambda child: repr(child), self._children
        )))

class ValAnything(Validator):
    """Validator allows all kind of values"""

    def validate(self, value: Any, context: str = '') -> None:
        pass

    def __repr__(self) -> str:
        return super().__repr__() + ' allows any value'

class ValNothing(Validator):
    """Validator denies any value with given reason"""

    def __init__(self, reason: str) -> None:
        self._reason = str(reason)

    @property
    def reason(self) -> str:
        return self._reason

    @reason.setter
    def reason(self, reason: str) -> None:
        self._reason = str(reason)

    def validate(self, value: Any, context: str = '') -> None:
        raise RuntimeError(f'{self._reason}; {context}')

    def __repr__(self) -> str:
        return super().__repr__() + f'({self._reason})'

class ValType(Validator):
    """Validator only accepts given type"""

    def __init__(self, T: Union[type, Sequence[type]]) -> None:
        if T is None:
            raise RuntimeError('A type must be given')
        if isinstance(T, type):
            self._T = T
        elif isinstance(T, Sequence):
            self._T = tuple(map(
                lambda t: t if isinstance(t, type) else type(t),
                T,
            ))
        else:
            self._T = type(T)

    @property
    def valid_type(self) -> type:
        return self._T

    def validate(self, value: Any, context: str = '') -> None:
        if not isinstance(value, self._T):
            raise TypeError(
                f'{self._T} value required but {type(value)} in {context}')

    def __repr__(self) -> str:
        return f'Validator for {self._T}'

class ValString(ValType):
    """
    Validator only accepts string with valid length

    Initialization arguments:
    - min_length --- minimal limit of string length, default is 0
    - max_length --- maximal limit of string length, default is -1 (no limit)

    Raises:
    - TypeError --- min_length and/or max_length are not intergers
    - ValueError --- max_length is non-negative but < min_length

    Properties:
    - min_length --- minimal limit of string length
    - max_length --- maximal limit of string length
    """

    def __init__(self, min_length: int = 0, max_length: int = -1) -> None:
        super().__init__(str)
        self.set_length_range(min_length, max_length)


    @property
    def min_length(self) -> int:
        """Get minimal limit of string length"""
        return self._min

    @property
    def max_length(self) -> int:
        """Get maximal limit of string length"""
        return self._max

    def set_length_range(
            self, min_length: int = 0, max_length: int = -1) -> None:
        """Set constraints on string length"""
        if not isinstance(min_length, int) or not isinstance(max_length, int):
            raise TypeError(
                f'Not intergers: {type(min_length)} {type(max_length)}')
        self._min = int(min_length)
        self._max = int(max_length)
        if self._min < 0:
            self._min = 0
        if self._max < 0:
            self._max = -1
        elif self._max < self._min:
            raise ValueError(f'max {max_length} < min {min_length}')

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        l = len(value)
        if self._min > 0 and l < self._min:
            raise ValueError(
                f'Require min length {self._min} but {l} in {context}')
        elif self._max >= 0 and l > self._max:
            raise ValueError(
                f'Require max length {self._max} but {l} in {context}')

    def __repr__(self) -> str:
        return super().__repr__() + f' ({self._min} ~ {self._max})'

class ValPattern(ValType):
    """
    Validator for strings with given pattern

    Args:
    - pattern --- the regular expression to define string pattern
    """

    def __init__(self, pattern: str) -> None:
        super().__init__(str)
        if not isinstance(pattern, str) or len(pattern) < 1:
            raise ValueError(f'Invalid pattern {pattern}')
        self._pattern = pattern

    @property
    def pattern(self) -> str:
        return self._pattern

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        match = re.match(self._pattern, value)
        if match is None or match.group() != value:
            raise ValueError(
                f'"{value}" dismatches pattern "{self._pattern}" in {context}')

    def __repr__(self) -> str:
        return super().__repr__() + f' (pattern: {self._pattern})'

class ValInt(ValType):
    """
    Validator accepts int or np.integer in given range

    Args:
    - min --- minimal value
    - max --- maximal value
    """

    _BIGGEST = int(0x7fffffff)

    def __init__(self, min: int = -_BIGGEST-1, max: int = _BIGGEST) -> None:
        super().__init__((int, np.integer))
        if not isinstance(min, int) or not isinstance(max, int):
            raise TypeError(
                f'invalid type of boundaries: {type(min)} {type(max)}')
        if min > max:
            raise ValueError(f'Invalid range: {min} ~ {max}')
        self._min = min
        self._max = max

    @property
    def min(self) -> int:
        return self._min

    @property
    def max(self) -> int:
        return self._max

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        if value < self._min or value > self._max:
            raise ValueError(
                f'{value} out of range [{self._min}, {self._max}] in {context}')

    def __repr__(self) -> str:
        return super().__repr__() + f' ({self._min} ~ {self._max})'


class ValQuantifiedInt(ValInt):
    """
    Validator accepts quantified integer in given range

    Args:
    - min --- minimal value
    - max --- maximal value
    - lsb --- least small bit, a.k.a. the unit of quantization
    """

    def __init__(self,
                 min: int = -ValInt._BIGGEST - 1,
                 max: int = ValInt._BIGGEST,
                 lsb: int = 5,) -> None:
        super().__init__(min, max)
        if not isinstance(lsb, int) or lsb <= 0:
            raise ValueError(f'Invalid LSB {lsb}')
        self._lsb = lsb

    @property
    def lsb(self) -> int:
        return self._lsb

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        if (value%self.lsb) != 0:
            raise ValueError(f'{value} is not quantified')

    def __repr__(self) -> str:
        return super().__repr__() + f' quantified by {self.lsb}'

class ValNumber(ValType):
    """
    Validator accepts all kinds of number value in given range

    Args:
    - min --- minimal value
    - max --- maximal value
    """

    def __init__(self,
                 min: float = -float('inf'),
                 max: float = float('inf')) -> None:
        super().__init__((int, float, np.integer, np.floating))
        if not isinstance(min, float) or not isinstance(max, float):
            raise TypeError(
                f'invalid type of boundaries: {type(min)} {type(max)}')
        if min > max:
            raise ValueError(f'Invalid range: {min} ~ {max}')
        self._min = min
        self._max = max

    @property
    def min(self) -> int:
        return self._min

    @property
    def max(self) -> int:
        return self._max

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        if value < self._min or value > self._max:
            raise ValueError(
                f'{value} out of range [{self._min}, {self._max}] in {context}')

    def __repr__(self) -> str:
        return super().__repr__() + f' ({self._min} ~ {self._max})'

class ValQuantifiedNumber(ValNumber):
    """
    Validator accepts quantified number value in given range

    Args:
    - min --- minimal value
    - max --- maximal value
    - lsb --- least small bit, a.k.a. the unit of quantization
    - thre --- threshold to check quantization, default use ``1e-3 * lsb``
    """

    def __init__(self,
                 min: float = -float('inf'),
                 max: float = float('inf'),
                 lsb: float = 1.0,
                 thre: float = 0.0) -> None:
        super().__init__(min, max)
        if not isinstance(lsb, float) or lsb < 1e-18:
            raise ValueError(f'Invalid LSB {lsb}')
        self._lsb = lsb
        if isinstance(thre, float) and thre > 0.0 and thre < lsb:
            self._thre = thre
        else:
            self._thre = lsb * 1e-3

    @property
    def lsb(self) -> float:
        return self._lsb

    @property
    def threshold(self) -> float:
        return self._thre

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        if (value%self.lsb) > self.threshold:
            raise ValueError(f'{value} is not quantified')

    def __repr__(self) -> str:
        return super().__repr__() + f' quantified by {self.lsb}'

class ValEnum(Validator):
    """Validator allows only one of given candidates"""

    def __init__(self, candidates: Sequence) -> None:
        if not isinstance(candidates, Sequence):
            raise TypeError(f'candidates must be a sequence')
        self._candidates = set(candidates)

    @property
    def candidates(self) -> Set:
        return self._candidates

    def validate(self, value: Any, context: str = '') -> None:
        if not value in self._candidates:
            raise ValueError(f'{value} is not a candidate in {context}')

    def __repr__(self) -> str:
        return super().__repr__() + ' ({})'.format(
            ', '.join(map(str, self._candidates)))

class ValSequence(Validator):
    """
    Validator requires value is a sequence of elements satisfying sub validator

    Property:
    - validator_of_element --- validator of element in sequence
    """

    def __init__(self, child: Optional[Validator] = None) -> None:
        """Initialization with optional validator of sequence element"""
        self._child = child if isinstance(child, Validator) else None

    @property
    def validator_of_element(self) -> Optional[Validator]:
        return self._child

    def validate(self, value: Any, context: str = '') -> None:
        if not isinstance(value, Sequence):
            raise TypeError(f'Required sequence but {type(value)} in {context}')
        if isinstance(self._child, Validator):
            for element in value:
                self._child.validate(element)

    def __repr__(self) -> str:
        if isinstance(self._child, Validator):
            return f'<ValSequence({self._child})>'
        return '<ValSequence>'


class ValRange(ValType):
    """
    Validator requires a pair of float numbers to represent a value range

    Args:
    - min --- minimal value
    - max --- maximal value
    - min_range --- minimal range, default is 0.0
    - max_range --- maximal range, default is infinite
    """

    def __init__(self,
                 min: float, max: float,
                 min_range: float = 0.0,
                 max_range: float = float('inf')) -> None:
        super().__init__(tuple)
        if not isinstance(min, float) or not isinstance(max, float):
            raise TypeError(f'Invalid input types {type(min)}, {type(max)}')
        if min < max:
            self._min = min
            self._max = max
        else:
            raise ValueError(f'Invalid interval {min} - {max}')
        self._min_range = min_range if isinstance(min_range, float) and \
            min_range > 0.0 else 0.0
        self._max_range = max_range if isinstance(max_range, float) and \
            max_range > min_range else float('inf')

    def validate(self, value: Any, context: str = '') -> None:
        super().validate(value, context)
        if len(value) != 2:
            raise ValueError(
                f'Invalid range element count {len(value)}, {context}')
        a, b = value
        if not isinstance(a, float) or not isinstance(b, float):
            raise TypeError(
                f'Invalid range element types {type(a)}, {type(b)}, {context}')
        if a > b or a < self._min or b > self._max or \
                (b-a) < self._min_range or (b-a) > self._max_range:
            raise ValueError(f'Invalid range {a}~{b}, {context}')

    def __repr__(self) -> str:
        return super().__repr__() + f'(range {self._min} ~ {self._max})'

if __name__ == '__main__':
    for value, validator in [
        ('5', ValType(str)),
        ('5', ValType(int)),
        (103, ValInt(max=100)),
        (52, ValQuantifiedInt(lsb=5)),
        (52, ValQuantifiedInt(lsb=2)),
        ('prettyage.new@gmail.com', ValPattern('\w+@\w+(\.\w+)+')),
        ('prettyage.new@gmail.com', ValPattern('\w+(\.\w+)*@\w+(\.\w+)+')),
        (12.3, ValNumber(0.0, 100.0)),
        (50.01, ValQuantifiedNumber(0.0, 100.0, 1.0)),
        (50.01, ValQuantifiedNumber(0.0, 100.0, 1.0, 0.1)),
        ('on', ValEnum(('on', 'off'))),
        ('job', ValEnum(('on', 'off'))),
        ([], ValSequence(ValInt())),
        ([-5, 6, 78], ValSequence(ValInt(0, 100))),
        (('5', 5), ValSequence()),
        ((0.0, 5.0), ValRange(0.0, 10.0, 1.0)),
        ((0.0, 60.0), ValRange(0.0, 100.0, 10.0, 50.0)),
    ]:
        rst = validate_value(value, validator, 'demo')
        print(f'validate {value} by {validator}: {rst}')
