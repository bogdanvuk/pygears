from pygears import alternative, gear, module
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Integer, Tuple, Number, Any, Bool, Integral
from pygears.util.hof import oper_tree
from pygears.hls import datagear


@datagear
def add(din: Tuple[{'a': Number, 'b': Number}]) -> b'din[0] + din[1]':
    return din[0] + din[1]


@alternative(add)
@gear(enablement=b'len(din) > 2')
def add_vararg(*din: Integer):
    return oper_tree(din, add)


@datagear
def div(din: Tuple[{'a': Number, 'b': Number}]) -> b'din[0] // din[1]':
    return din[0] // din[1]


@datagear
def eq(din: Tuple[{'a': Any, 'b': Any}]) -> Bool:
    return din[0] == din[1]


@datagear
def ge(din: Tuple[{'a': Number, 'b': Number}]) -> Bool:
    return din[0] >= din[1]


@datagear
def gt(din: Tuple[{'a': Number, 'b': Number}]) -> Bool:
    return din[0] > din[1]


@datagear
def invert(a) -> b'a':
    return ~a


@datagear
def le(din: Tuple[{'a': Number, 'b': Number}]) -> Bool:
    return din[0] <= din[1]


@datagear
def lt(din: Tuple[{'a': Number, 'b': Number}]) -> Bool:
    return din[0] < din[1]


@datagear
def mod(din: Tuple[Integer, Integer]) -> b'din[0] % din[1]':
    return din[0] % din[1]


@datagear
def mul(din: Tuple[{'a': Number, 'b': Number}]) -> b'din[0] * din[1]':
    return din[0] * din[1]


@datagear
def ne(din: Tuple[Any, Any]) -> Bool:
    return din[0] != din[1]


@datagear
def neg(a: Number) -> b'-a':
    return -a


@datagear
def sub(din: Tuple[{'a': Number, 'b': Number}]) -> b'din[0] - din[1]':
    return din[0] - din[1]


@datagear
def shl(din: Integral, *, shamt) -> b'din << shamt':
    return module().tout(din << shamt)


@datagear
def shr(din: Integral, *, shamt) -> b'din >> shamt':
    return module().tout(din >> shamt)


@datagear
def xor(din: Tuple[Integral, Integral]) -> b'din[0] ^ din[1]':
    return din[0] ^ din[1]


class AddIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__add__', add)
        safe_bind('gear/intf_oper/__floordiv__', div)
        safe_bind('gear/intf_oper/__eq__', eq)
        safe_bind('gear/intf_oper/__ge__', ge)
        safe_bind('gear/intf_oper/__gt__', gt)
        safe_bind('gear/intf_oper/__invert__', invert)
        safe_bind('gear/intf_oper/__le__', le)
        safe_bind('gear/intf_oper/__lt__', lt)
        safe_bind('gear/intf_oper/__lshift__', lambda x, y: shl(x, shamt=y))
        safe_bind('gear/intf_oper/__mod__', mod)
        safe_bind('gear/intf_oper/__mul__', mul)
        safe_bind('gear/intf_oper/__ne__', ne)
        safe_bind('gear/intf_oper/__neg__', neg)
        safe_bind('gear/intf_oper/__rshift__', lambda x, y: shr(x, shamt=y))
        safe_bind('gear/intf_oper/__sub__', sub)
        safe_bind('gear/intf_oper/__xor__', xor)
