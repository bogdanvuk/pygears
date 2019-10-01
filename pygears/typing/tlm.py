import inspect

from .base import EnumerableGenericMeta


class TLMMeta(EnumerableGenericMeta):
    def __getitem__(self, index):
        if not self.specified:
            return super().__getitem__(index)

        index = self.index_norm(index)

        if len(index) != 1:
            raise IndexError

        return self.args[0]


class TLM(metaclass=TLMMeta):
    __parameters__ = ['T']
