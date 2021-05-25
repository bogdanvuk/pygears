from pygears.conf import PluginBase, reg

# from .bool import Bool
from .queue import Queue
from .array import Array
from .base import TemplateArgumentsError, typeof, Any, is_type, T
from .tuple import Tuple
from .uint import Int, Uint, Integer, Bool, Integral, code, decode
from .unit import Unit
from .union import Union, Maybe, some, Nothing
from .math import bitw, ceil_pow2, div, floor
from .tlm import TLM
from .flatten import flatten
from .expand import expand
from .factor import factor
from .fixp import Fixp, Ufixp, Fixpnumber
from .number import Number
from .float import Float
from .cast import cast, signed
from .saturate import saturate
from .qround import qround
from .match import get_match_conds, TypeMatchError, match
from .trunc import trunc

__all__ = [
    'Bool', 'Queue', 'TemplateArgumentsError', 'Tuple', 'Int', 'Uint', 'Unit', 'Union',
    'Maybe', 'Array', 'Float', 'bitw', 'div', 'floor', 'typeof', 'Any', 'TLM',
    'ceil_pow2', 'is_type', 'flatten', 'expand', 'factor', 'Ufixp', 'Fixp', 'Number',
    'Fixpnumber', 'Integral', 'cast', 'signed', 'code', 'decode',
    'saturate', 'qround', 'get_match_conds', 'TypeMatchError', 'match', 'trunc', 'T'
]


class TypingNamespacePlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['gear/type_arith'] = {}


class CoreTypesPlugin(TypingNamespacePlugin):
    @classmethod
    def bind(cls):
        reg['gear/type_arith/Union'] = Union
        reg['gear/type_arith/Tuple'] = Tuple
        reg['gear/type_arith/Uint'] = Uint
        reg['gear/type_arith/Float'] = Float
        reg['gear/type_arith/Int'] = Int
        reg['gear/type_arith/Integer'] = Integer
        reg['gear/type_arith/Integral'] = Integral
        reg['gear/type_arith/Unit'] = Unit
        reg['gear/type_arith/Fixp'] = Fixp
        reg['gear/type_arith/Ufixp'] = Ufixp
        reg['gear/type_arith/Bool'] = Bool
        reg['gear/type_arith/Queue'] = Queue
        reg['gear/type_arith/Array'] = Array
        reg['gear/type_arith/bitw'] = bitw
        reg['gear/type_arith/ceil_pow2'] = ceil_pow2
        reg['gear/type_arith/typeof'] = typeof
        reg['gear/type_arith/Any'] = Any
        reg['gear/type_arith/TLM'] = TLM
        reg['gear/type_arith/flatten'] = flatten
        reg['gear/type_arith/expand'] = expand
        reg['gear/type_arith/factor'] = factor
        reg['gear/type_arith/cast'] = cast
