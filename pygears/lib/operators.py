from pygears import alternative, gear, module, reg
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Any, Bool, Integer, Integral, Number, Tuple
from pygears.typing import div as typing_div, is_type, Uint, typeof
from pygears.typing import code as type_code
from pygears.util.hof import oper_tree
from pygears import datagear
from pygears.hdl.util import HDLGearHierVisitor
from pygears.hdl import flow_visitor
from pygears.hdl.sv import SVGenPlugin
from pygears.hdl.v import VGenPlugin

# TODO: Think about operand promoting (casting). What if a: Int[32] and someone
# writes a == 0? Which type should the 0 be?

@datagear
def add(din: Tuple[{'a': Number, 'b': Number}]) -> b'din[0] + din[1]':
    return din[0] + din[1]


@alternative(add)
@gear(enablement=b'len(din) > 2')
def add_vararg(*din: Number):
    return oper_tree(din, add)


@datagear
def and_(din: Tuple[Integral, Integral]) -> b'din[0] & din[1]':
    return din[0] & din[1]


@datagear
def fdiv(din: Tuple[{'a': Integer, 'b': Integer}]) -> b'din[0] // din[1]':
    return din[0] // din[1]


@datagear
def cat(din: Tuple[{'a': Uint, 'b': Uint}]) -> b'din[0] @ din[1]':
    return din[0] @ din[1]


@datagear
def div(
        din: Tuple[{
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
def code(din, *, t) -> b't':
    return type_code(din, t)


@datagear
def xor(din: Tuple[Integral, Integral]) -> b'din[0] ^ din[1]':
    return din[0] ^ din[1]


def shr_or_code(x, y):
    if is_type(y):
        if typeof(y, Uint) and (not y.specified):
            y = Uint[x.dtype.width]

        return code(x, t=y)
    else:
        return shr(x, shamt=y)


class AddIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        reg['gear/intf_oper/__add__'] = add
        reg['gear/intf_oper/__and__'] = and_
        reg['gear/intf_oper/__floordiv__'] = fdiv
        reg['gear/intf_oper/__truediv__'] = or_
        reg['gear/intf_oper/__eq__'] = eq
        reg['gear/intf_oper/__ge__'] = ge
        reg['gear/intf_oper/__gt__'] = gt
        reg['gear/intf_oper/__invert__'] = invert
        reg['gear/intf_oper/__le__'] = le
        reg['gear/intf_oper/__lt__'] = lt
        reg['gear/intf_oper/__lshift__'] = lambda x, y: shl(x, shamt=y)
        reg['gear/intf_oper/__matmul__'] = cat
        reg['gear/intf_oper/__mod__'] = mod
        reg['gear/intf_oper/__mul__'] = mul
        reg['gear/intf_oper/__ne__'] = ne
        reg['gear/intf_oper/__neg__'] = neg
        reg['gear/intf_oper/__rshift__'] = shr_or_code
        reg['gear/intf_oper/__sub__'] = sub
        reg['gear/intf_oper/__xor__'] = xor


@flow_visitor
class RemoveRecode(HDLGearHierVisitor):
    def code(self, node):
        pout = node.out_ports[0]
        pin = node.in_ports[0]

        if getattr(pin.dtype, 'width', 0) == getattr(pout.dtype, 'width', 0):
            node.bypass()


class HDLCodePlugin(VGenPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        reg['vgen/flow'].insert(0, RemoveRecode)
        reg['svgen/flow'].insert(0, RemoveRecode)
