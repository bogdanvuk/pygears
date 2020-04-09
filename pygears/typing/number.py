from .base import GenericMeta
from abc import ABCMeta, abstractmethod


class NumberType(ABCMeta, GenericMeta):
    @property
    @abstractmethod
    def signed(self) -> bool:
        ...


class Number(metaclass=NumberType):
    """All numbers inherit from this class.
    If you just want to check if an argument x is a number, without
    caring what kind, use isinstance(x, Number).
    """
    __slots__ = ()

    # Concrete numeric types must provide their own hash implementation
    __hash__ = None


# class Number(int, metaclass=NumberType):
#     pass
