from pygears import alternative, gear, module
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Any, Bool, Integer, Integral, Number, Tuple
from pygears.typing import div as typing_div, is_type, Uint, typeof
from pygears.typing import reinterpret as type_reinterpret
from pygears.util.hof import oper_tree
from pygears.hls import datagear
from pygears.rtl.gear import RTLGearHierVisitor
from pygears.rtl import flow_visitor
from pygears.hdl.sv import SVGenPlugin
from pygears.hdl.v import VGenPlugin


@datagear
def add(din: Tuple[{'a': Number, 'b': Number}]) -> b'din[0] + din[1]':
    return din[0] + din[1]


@alternative(add)
@gear(enablement=b'len(din) > 2')
def add_vararg(*din: Integer):
    return oper_tree(din, add)


@datagear
def and_(din: Tuple[Integral, Integral]) -> b'din[0] & din[1]':
    return din[0] & din[1]


@datagear
def fdiv(din: Tuple[{'a': Integer, 'b': Integer}]) -> b'din[0] // din[1]':
    return din[0] // din[1]


@datagear
def div(din: Tuple[{
        'a': Number,
        'b': Number
}], *, subprec) -> b'typing_div(din[0], din[1], subprec)':
    return typing_div(din[0], din[1], subprec)


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
def or_(din: Tuple[Integral, Integral]) -> b'din[0] | din[1]':
    return din[0] | din[1]


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
def reinterpret(din, *, t) -> b't':
    return type_reinterpret(din, t)


@datagear
def xor(din: Tuple[Integral, Integral]) -> b'din[0] ^ din[1]':
    return din[0] ^ din[1]


def shr_or_reinterpret(x, y):
    if is_type(y):
        if typeof(y, Uint) and (not y.specified):
            y = Uint[x.dtype.width]

        return reinterpret(x, t=y)
    else:
        return shr(x, shamt=y)


class AddIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__add__', add)
        safe_bind('gear/intf_oper/__and__', and_)
        safe_bind('gear/intf_oper/__floordiv__', fdiv)
        safe_bind('gear/intf_oper/__truediv__', or_)
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
        safe_bind('gear/intf_oper/__rshift__', shr_or_reinterpret)
        safe_bind('gear/intf_oper/__sub__', sub)
        safe_bind('gear/intf_oper/__xor__', xor)


@flow_visitor
class SVRemoveReplicate(RTLGearHierVisitor):
    def reinterpret(self, node):
        node.bypass()


class RTLReinterpretPlugin(VGenPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['vgen']['flow'].insert(0, SVRemoveReplicate)
        cls.registry['svgen']['flow'].insert(0, SVRemoveReplicate)
