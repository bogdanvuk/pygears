from pygears.core.registry import PluginBase
from pygears.typing import Union, Tuple, Uint, Int, Unit, Bool, Queue, Array, bitw


class TypingNamespacePlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['TypeArithNamespace'] = {}


class CoreTypesPlugin(TypingNamespacePlugin):
    @classmethod
    def bind(cls):
        cls.registry['TypeArithNamespace']['Union'] = Union
        cls.registry['TypeArithNamespace']['Tuple'] = Tuple
        cls.registry['TypeArithNamespace']['Uint'] = Uint
        cls.registry['TypeArithNamespace']['Int'] = Int
        cls.registry['TypeArithNamespace']['Unit'] = Unit
        cls.registry['TypeArithNamespace']['Bool'] = Bool
        cls.registry['TypeArithNamespace']['Queue'] = Queue
        cls.registry['TypeArithNamespace']['Array'] = Array
        cls.registry['TypeArithNamespace']['bitw'] = bitw
