from pygears.registry import PluginBase

from .bool import Bool
from .queue import Queue
from .array import Array
from .base import TemplateArgumentsError, typeof, Any
from .tuple import Tuple
from .uint import Int, Uint, Integer
from .unit import Unit
from .union import Union
from .bitw import bitw, ceil_pow2
from .tlm import TLM

__all__ = [
    'Bool', 'Queue', 'TemplateArgumentsError', 'Tuple', 'Int', 'Uint', 'Unit',
    'Union', 'Array', 'bitw', 'typeof', 'Any', 'TLM', 'ceil_pow2'
]


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
        cls.registry['TypeArithNamespace']['Integer'] = Integer
        cls.registry['TypeArithNamespace']['Unit'] = Unit
        cls.registry['TypeArithNamespace']['Bool'] = Bool
        cls.registry['TypeArithNamespace']['Queue'] = Queue
        cls.registry['TypeArithNamespace']['Array'] = Array
        cls.registry['TypeArithNamespace']['bitw'] = bitw
        cls.registry['TypeArithNamespace']['ceil_pow2'] = ceil_pow2
        cls.registry['TypeArithNamespace']['typeof'] = typeof
        cls.registry['TypeArithNamespace']['Any'] = Any
        cls.registry['TypeArithNamespace']['TLM'] = TLM
