from pygears.conf import PluginBase, safe_bind

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
        safe_bind('gear/type_arith', {})


class CoreTypesPlugin(TypingNamespacePlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/type_arith/Union', Union)
        safe_bind('gear/type_arith/Tuple', Tuple)
        safe_bind('gear/type_arith/Uint', Uint)
        safe_bind('gear/type_arith/Int', Int)
        safe_bind('gear/type_arith/Integer', Integer)
        safe_bind('gear/type_arith/Unit', Unit)
        safe_bind('gear/type_arith/Bool', Bool)
        safe_bind('gear/type_arith/Queue', Queue)
        safe_bind('gear/type_arith/Array', Array)
        safe_bind('gear/type_arith/bitw', bitw)
        safe_bind('gear/type_arith/ceil_pow2', ceil_pow2)
        safe_bind('gear/type_arith/typeof', typeof)
        safe_bind('gear/type_arith/Any', Any)
        safe_bind('gear/type_arith/TLM', TLM)
