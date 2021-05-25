import ast as opc
import inspect
import attr
import typing
import textwrap
from dataclasses import dataclass, field

from pygears.typing.base import TypingMeta, GenericMeta, class_and_instance_method, is_type
from functools import reduce
from pygears import Intf
from pygears.core.port import InPort, OutPort
from pygears.core.gear import InSig, OutSig
from pygears.typing import (Bool, Integer, Queue, Tuple, Uint, is_type, typeof, Array, Union, Unit,
                            cast, code, Nothing)
# from .ast.utils import get_property_type
import operator

BOOLEAN_OPERATORS = {opc.BitOr, opc.BitAnd, opc.BitXor, opc.Invert, opc.Not, opc.And, opc.Or}
BIN_OPERATORS = [opc.Eq, opc.Gt, opc.GtE, opc.Lt, opc.LtE, opc.NotEq, opc.And, opc.Or]

COMMUTATIVE_BIN_OPERATORS = [
    opc.Add, opc.Mult, opc.BitOr, opc.BitAnd, opc.BitXor, opc.And, opc.Or, opc.Eq
]

ARITH_BIN_OPERATORS = [
    opc.Add, opc.Sub, opc.Mult, opc.Div, opc.Mod, opc.Pow, opc.LShift, opc.RShift, opc.BitOr,
    opc.BitAnd, opc.BitXor, opc.Div
]

EXTENDABLE_OPERATORS = [
    opc.Add, opc.Sub, opc.Mult, opc.Div, opc.Mod, opc.Pow, opc.LShift, opc.RShift, opc.BitOr,
    opc.BitAnd, opc.BitXor, opc.Div, opc.Invert, opc.Not
]

OPMAP = {
    opc.Add: '+',
    opc.Sub: '-',
    opc.MatMult: '@',
    opc.Mult: '*',
    opc.Div: '/',
    opc.Mod: '%',
    opc.Pow: '**',
    opc.LShift: '<<',
    opc.RShift: '>>',
    opc.BitOr: '|',
    opc.BitAnd: '&',
    opc.BitXor: '^',
    opc.FloorDiv: '/',
    opc.Invert: '~',
    opc.Not: '!',
    opc.UAdd: '+',
    opc.USub: '-',
    opc.Eq: '==',
    opc.Gt: '>',
    opc.GtE: '>=',
    opc.Lt: '<',
    opc.LtE: '<=',
    opc.NotEq: '!=',
    opc.And: '&&',
    opc.Or: '||'
}

PYOPMAP = {
    opc.Add: operator.__add__,
    opc.And: operator.__and__,
    opc.BitAnd: operator.__and__,
    opc.BitOr: operator.__or__,
    opc.BitXor: operator.__xor__,
    opc.Div: operator.__truediv__,
    opc.Eq: operator.__eq__,
    opc.Gt: operator.__gt__,
    opc.GtE: operator.__ge__,
    opc.FloorDiv: operator.__floordiv__,
    opc.Lt: operator.__lt__,
    opc.LtE: operator.__le__,
    opc.LShift: operator.__lshift__,
    opc.MatMult: operator.__matmul__,
    opc.Mult: operator.__mul__,
    opc.NotEq: operator.__ne__,
    opc.Not: operator.__not__,
    opc.Or: operator.__or__,
    opc.RShift: operator.__rshift__,
    opc.Sub: operator.__sub__,
    opc.UAdd: operator.__pos__,
    opc.USub: operator.__neg__,
}

REDUCE_INITIAL = {
    opc.Add: 0,
    opc.And: True,
    opc.BitAnd: True,
    opc.BitOr: False,
    opc.Mult: 1,
    opc.Or: False,
}


def opex(op, *operands):
    try:
        if op in BIN_OPERATORS or op is opc.Not:
            res_type = Bool
        else:
            res_type = PYOPMAP[op](*(p.dtype for p in operands))

        return res_type(PYOPMAP[op](*(p.val for p in operands)))
    except:
        return PYOPMAP[op](*(p.val for p in operands))


def find_sub_dtype(val):
    if isinstance(val, (tuple, list)):
        sub = max(val, key=lambda x: getattr(x, 'dtype').width)
        return type(sub)

    return type(val)


def find_name(node):
    name = getattr(node, 'name', None)
    if name is not None:
        return name

    if hasattr(node, 'val'):
        return find_name(node.val)

    if hasattr(node, 'op'):
        return find_name(node.op)

    return None


def get_contextpr(node):
    if isinstance(node, ResExpr):
        return node.val

    # TODO: rethink this? This should be some sort of named constant expression?
    if isinstance(node, Name):
        obj = node.obj
        if isinstance(obj, Variable) and obj.val is not None and not obj.reg:
            return obj.val

    return None


class IntfTypeMeta(GenericMeta):
    iin = 0
    iout = 1

    @property
    def dtype(self):
        return self.args[0]

    @property
    def direction(self):
        return self.args[1]


class IntfType(tuple, metaclass=IntfTypeMeta):
    __parameters__ = ['dtype', 'direction']

    def pull_nb(self):
        pass

    def empty(self):
        pass

    def ack(self):
        pass


@attr.s(auto_attribs=True, kw_only=True)
class Expr:
    @property
    def dtype(self):
        pass


# Type aliases

PgType = typing.Union[TypingMeta, Unit, int]
OpType = typing.Union[Expr, PgType, str]

# Type definitions


class EmptyTypeMeta(GenericMeta):
    @property
    def dtype(self):
        if self.args:
            return self.args[0]
        else:
            return None


class EmptyType(metaclass=EmptyTypeMeta):
    __parameters__ = ['dtype']

    def __init__(self, v=None):
        if (v is not None) and (not isinstance(v, EmptyType)):
            raise TypeError

    def __hash__(self):
        if type(self).dtype is None:
            return hash(type(self))
        else:
            return hash((type(self), type(self).dtype))

    def __repr__(self):
        if type(self).dtype is None:
            return 'Empty'
        else:
            return f'{repr(type(self).dtype)}(Empty)'


class ResExpr(Expr):
    def __new__(cls, val):
        if isinstance(val, Expr):
            return val

        inst = super().__new__(cls)

        # TODO: Think about this automatic casting. For example when register
        # is inferred based on this value, it might be wrong. ex. "cnt = 0"
        if not is_type(type(val)) and isinstance(val, (int, float)):
            val = cast(val, Integer)

        inst.val = val

        return inst

    def __init__(self, val):
        super().__init__()

    def __eq__(self, other):
        if not isinstance(other, ResExpr):
            return False

        return self.val == other.val

    def __hash__(self):
        return hash((self.val, type(self)))

    def __repr__(self):
        return f'ResExpr({repr(self.val)})'

    def __str__(self):
        return str(self.val)

    @property
    def dtype(self):
        if isinstance(self.val, EmptyType):
            if type(self.val).dtype is None:
                return EmptyType
            else:
                return type(self.val).dtype

        # if is_type(type(self.val)):
        #     return type(self.val)

        if not is_type(type(self.val)) and isinstance(self.val, int):
            return type(Integer(self.val))

        # TODO: Remove this if unecessary
        if isinstance(self.val, Intf):
            return IntfType[self.val.dtype]

        return type(self.val)

        # return None


res_true = ResExpr(Bool(True))
res_false = ResExpr(Bool(False))


@dataclass
class TupleExpr(Expr):
    val: typing.Sequence

    def __getitem__(self, key):
        return self.val[key]


@dataclass
class Variable:
    name: str
    dtype: typing.Union[PgType, typing.Any] = None
    val: typing.Union[PgType, Expr] = None
    any_init: Bool = False
    reg: Bool = False

    def __post_init__(self):
        if self.dtype is None:
            if self.val is not None:
                self.dtype = self.val.dtype


@dataclass
class Interface(Expr):
    intf: typing.Union[InPort, OutPort, Expr]
    direction: str
    _name: str = None

    @property
    def name(self):
        if self._name:
            return self._name
        try:
            return self.intf.basename
        except AttributeError:
            return find_name(self.intf)

    def __str__(self):
        return self.name

    @property
    def dtype(self):
        return find_sub_dtype(self.intf)


@attr.s(auto_attribs=True)
class Name(Expr):
    name: str
    obj: Variable = None
    ctx: str = 'load'

    def __repr__(self):
        return f'Id({self.name})'

    def __str__(self):
        if self.ctx in ['load', 'store']:
            return self.name
        else:
            return f'{self.name}.{self.ctx}'

    @property
    def dtype(self):
        return self.obj.dtype


@attr.s(auto_attribs=True)
class Component(Expr):
    val: Expr
    field: str

    def __repr__(self):
        return f'{repr(self.val)}.{self.field}'

    def __str__(self):
        return f'{self.val}.{self.field}'

    @property
    def dtype(self):
        if self.field in ['ready', 'valid']:
            return Bool
        elif self.field == 'data':
            assert typeof(self.val.dtype, IntfType)
            return self.val.dtype.dtype


@dataclass
class ConcatExpr(Expr):
    def __repr__(self):
        return 'ConcatExpr(' + ', '.join([repr(v) for v in self.operands]) + ')'

    def __str__(self):
        return '(' + ', '.join([str(v) for v in self.operands]) + ')'

    def __init__(self, operands: typing.Sequence[Expr]):
        pass

    def __eq__(self, other):
        if not isinstance(other, BinOpExpr):
            return False

        return all(ops == opo for ops, opo in zip(self.operands, other.operands))

    def __new__(cls, operands: typing.Sequence[Expr]):
        if all(isinstance(v, ResExpr) for v in operands):
            if (all(is_type(v.dtype) for v in operands)
                    and not any(isinstance(v.val, EmptyType) for v in operands)):
                return ResExpr(Tuple[tuple(v.dtype for v in operands)](tuple(v.val
                                                                             for v in operands)))
            else:
                return ResExpr(tuple(v.val for v in operands))

        inst = super().__new__(cls)
        inst.operands = operands

        return inst

    @property
    def dtype(self):
        return Tuple[tuple(op.dtype for op in self.operands)]


class UnaryOpExpr(Expr):
    def __init__(self, operand, operator):
        pass

    def __repr__(self):
        return f'{OPMAP[self.operator]}({self.operand})'

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return (self.operand == other.operand and self.operator == other.operator)

    def __new__(cls, operand, operator):
        if isinstance(operand, ResExpr):
            return ResExpr(opex(operator, operand))

        if operator == opc.Not and isinstance(operand, BinOpExpr):
            if operand.operator == opc.Eq:
                return BinOpExpr(operand.operands, opc.NotEq)

            if operand.operator == opc.NotEq:
                return BinOpExpr(operand.operands, opc.Eq)

            # De-Morgan laws
            if operand.operator in [opc.And, opc.Or]:
                operands = [UnaryOpExpr(op, opc.Not) for op in operand.operands]
                return BinOpExpr(operands, opc.Or if operand.operator == opc.And else opc.And)

        elif operator == opc.Not and isinstance(operand, ConditionalExpr):
            op1, op2 = operand.operands
            if typeof(op1.dtype, (Uint[1], Bool)) and typeof(op2.dtype, (Uint[1], Bool)):
                return ConditionalExpr([UnaryOpExpr(op1, opc.Not),
                                        UnaryOpExpr(op2, opc.Not)], operand.cond)

        elif operator == opc.Not and isinstance(operand,
                                                UnaryOpExpr) and operand.operator == opc.Not:
            return operand.operand

        inst = super().__new__(cls)
        inst.operand = operand
        inst.operator = operator
        return inst

    @property
    def dtype(self):
        if self.operator == opc.Not:
            return Uint[1]

        res_t = eval(f'{OPMAP[self.operator]} op', {'op': self.operand.dtype})

        if isinstance(res_t, bool):
            return Uint[1]

        return res_t


class CastExpr(Expr):
    def __init__(self, operand, cast_to):
        pass

    def __repr__(self):
        return f'CastTo({self.operand}, {self.cast_to})'

    def __str__(self):
        return f"({self.cast_to})'({self.operand})"

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return (self.operand == other.operand and self.cast_to == other.cast_to)

    def __new__(cls, operand, cast_to):
        if isinstance(cast_to, ResExpr):
            cast_to = cast_to.val

        if cast_to == int:
            cast_to = Uint[operand.dtype.width]

        if operand.dtype == cast_to:
            return operand

        if isinstance(operand, ResExpr):
            return ResExpr(code(operand.val, cast_to))

        if isinstance(operand, ConcatExpr) and typeof(cast_to, (Array, Tuple, Queue, Union)):
            cast_ops = [
                CastExpr(op, cast_t) if op.dtype != cast_t else op
                for op, cast_t in zip(operand.operands, cast_to)
            ]
            operand = ConcatExpr(cast_ops)

        inst = super().__new__(cls)
        inst.operand = operand
        inst.cast_to = cast_to
        return inst

    @property
    def dtype(self):
        return self.cast_to


class SliceExpr(Expr):
    def __repr__(self):
        return f'({self.start if self.start else ""}:{self.stop if self.stop else ""}:{self.step if self.step else ""})'

    def __init__(self, start: OpType, stop: OpType, step: OpType):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return (self.start == other.start and self.stop == other.stop and self.step == other.step)

    def __new__(cls, start: OpType, stop: OpType, step: OpType):
        if isinstance(start, ResExpr) and isinstance(stop, ResExpr) and isinstance(step, ResExpr):
            return ResExpr(slice(start.val, stop.val, step.val))

        inst = super().__new__(cls)
        inst.start = start
        inst.stop = stop
        inst.step = step
        return inst


def identity_anihilation(op1, op2, operator):
    '''
    x && True => x
    x || False => x

    x && False => False
    x || True => True
    '''
    if operator == opc.And:
        if isinstance(op1, ResExpr):
            return op2 if op1.val else op1

    elif operator == opc.Or:
        if isinstance(op1, ResExpr):
            return op1 if op1.val else op2

    return None


def idempotence(op1, op2, operator):
    '''
    x && x => x
    x || x => x
    '''
    if operator in [opc.And, opc.Or, opc.BitAnd, opc.BitOr]:
        if op1 == op2:
            return op1

    return None


def complementation(op1, op2, operator):
    '''
    x && (~x) => False
    x || (~x) => True
    '''
    if isinstance(op1, UnaryOpExpr) and op1.operator == opc.Not:
        if op1.operand == op2:
            if operator is opc.And:
                return res_false
            elif operator is opc.Or:
                return res_true

    return None


def absorption(op1, op2, operator):
    '''
    x && (x || y) => x
    x || (x && y) => x

    x && ((~x) || y) => x && y
    x || ((~x) && y) => x || y
    '''
    if not isinstance(op2, BinOpExpr):
        return None

    op2_1, op2_2 = op2.operands
    if ((operator is opc.And and op2.operator is opc.Or)
            or (operator is opc.Or and op2.operator is opc.And)):
        if op1 == op2_1:
            return op2_1
        elif op1 == op2_2:
            return op2_2
        elif op1 == UnaryOpExpr(op2_1, opc.Not):
            return BinOpExpr([op1, op2_2], operator)
        elif op1 == UnaryOpExpr(op2_2, opc.Not):
            return BinOpExpr([op1, op2_1], operator)

    return None


def elimination(op1, op2, operator):
    '''
    (x && y) || (x && (~y)) => x
    (x || y) && (x || (~y)) => x
    '''
    if not (isinstance(op1, BinOpExpr) and isinstance(op2, BinOpExpr)):
        return None

    if op1.operator not in [opc.And, opc.Or] or op2.operator not in [opc.And, opc.Or]:
        return None

    if op1.operator != op2.operator or op1.operator == operator:
        return None

    op2_1, op2_2 = op2.operands
    for op1_1, op1_2 in [op1.operands, op1.operands[::-1]]:
        if op1_1 == op2_1 and op1_2 == UnaryOpExpr(op2_2, opc.Not):
            return op1_1
        elif op1_1 == op2_2 and op1_2 == UnaryOpExpr(op2_1, opc.Not):
            return op1_1

    return None


# def elimination_same(op1, op2, operator):
#     '''
#     x && (x && y) => x && y
#     x || (x || y) => x || y
#     x && ((~x) && y) => y
#     x || ((~x) || y) => True
#     '''
#     if not isinstance(op2, BinOpExpr) or operator != op2.operator:
#         return None

#     if op1.operator not in [opc.And, opc.Or] or op2.operator not in [opc.And, opc.Or]:
#         return None

#     if op1.operator != op2.operator or op1.operator == operator:
#         return None

#     op2_1, op2_2 = op2.operands
#     for op1_1, op1_2 in [op1.operands, op1.operands[::-1]]:
#         if op1_1 == op2_1 and op1_2 == UnaryOpExpr(op2_2, opc.Not):
#             return op1_1
#         elif op1_1 == op2_2 and op1_2 == UnaryOpExpr(op2_1, opc.Not):
#             return op1_1

#     return None


def booleq(op1, op2, operator):
    if operator not in [opc.Eq, opc.NotEq]:
        return

    if not (typeof(op1.dtype, (Bool, Uint[1])) and typeof(op2.dtype, (Bool, Uint[1]))):
        return

    if op2 == res_true:
        return op1 if operator == opc.Eq else UnaryOpExpr(op1, opc.Not)

    if op2 == res_false:
        return op1 if operator == opc.NotEq else UnaryOpExpr(op1, opc.Not)

    return None


def conditional_distribution(op1, op2, operator):
    if operator not in ARITH_BIN_OPERATORS:
        return None

    if (isinstance(op2, ConditionalExpr) and isinstance(op2.operands[0], ResExpr)
            and isinstance(op2.operands[1], ResExpr)):

        return ConditionalExpr([
            ResExpr(opex(operator, op1, op2.operands[0])),
            ResExpr(opex(operator, op1, op2.operands[1]))
        ], op2.cond)


bin_op_transforms = [
    identity_anihilation,
    idempotence,
    complementation,
    absorption,
    elimination,
    booleq,
    conditional_distribution,
]


# TODO: Should be allow BinOpExpr to have arbitrary number of boolean
# variables. This would allow for some simplfifications, ex. : (~x && y) && (x && ~y)
class BinOpExpr(Expr):
    def __repr__(self):
        try:
            return (f'{type(self).__name__}(operands={repr(self.operands)}, '
                    f'operator={self.operator.__name__})')
        except:
            return (f'{type(self).__name__}(operands={repr(self.operands)}, '
                    f'operator={self.operator})')

    def __str__(self):
        return f'({self.operands[0]} {OPMAP[self.operator]} {self.operands[1]})'

    def __init__(self, operands: typing.Tuple[OpType], operator):
        pass

    def __new__(cls, operands: typing.Tuple[OpType], operator):
        if len(operands) > 2:
            op1 = operands[0]
            op2 = BinOpExpr(operands[1:], operator)
        else:
            op1, op2 = operands

        if isinstance(op1, ResExpr) and isinstance(op2, ResExpr):
            return ResExpr(opex(operator, op1, op2))

        for t in bin_op_transforms:
            ret = t(op1, op2, operator)
            if ret is not None:
                return ret

        if operator in COMMUTATIVE_BIN_OPERATORS:
            for t in bin_op_transforms:
                ret = t(op2, op1, operator)
                if ret is not None:
                    return ret

        if operator in (opc.RShift, opc.LShift):
            if isinstance(op2, ResExpr) and op2.val == 0:
                return op1

        inst = super().__new__(cls)
        inst.operands = operands
        inst.operator = operator
        return inst

    def __eq__(self, other):
        if not isinstance(other, BinOpExpr):
            return False

        return ((self.operator == other.operator)
                and (all(ops == opo for ops, opo in zip(self.operands, other.operands))))

    @property
    def dtype(self):
        if self.operator in BIN_OPERATORS:
            return Uint[1]

        if (self.operator in (opc.LShift, opc.RShift)) and isinstance(self.operands[1], ResExpr):
            op2 = self.operands[1].val
        else:
            op2 = self.operands[1].dtype

        res_t = eval(f'op1 {OPMAP[self.operator]} op2', {'op1': self.operands[0].dtype, 'op2': op2})

        if isinstance(res_t, bool):
            return Uint[1]

        return res_t


class ArrayOpExpr(Expr):
    def __repr__(self):
        return f'{type(self).__name__}(val={repr(self.array)}, op={repr(self.operator)})'

    def __str__(self):
        return f'{OPMAP[self.operator]}({str(self.array)})'

    def __init__(self, array: Expr, operator):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return self.operator == other.operator and self.array == other.array

    def __new__(cls, array: Expr, operator):
        if isinstance(array, ResExpr):
            return ResExpr(reduce(PYOPMAP[operator], array.val, REDUCE_INITIAL[operator]))

        inst = super().__new__(cls)
        inst.array = array
        inst.operator = operator

        return inst

    @property
    def dtype(self):
        return self.array.dtype[0]


class SubscriptExpr(Expr):
    def __repr__(self):
        return f'{type(self).__name__}(val={repr(self.val)}, index={repr(self.index)}, ctx={self.ctx})'

    def __str__(self):
        return f'{self.val}[{self.index}]'

    def __init__(self, val: Expr, index: Expr, ctx: str = 'load'):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return self.val == other.val and self.index == other.index

    def __new__(cls, val: Expr, index: Expr, ctx: str = 'load'):
        const_index = get_contextpr(index)
        const_val = get_contextpr(val)
        if const_index is not None:
            if const_val is not None:
                return ResExpr(const_val[const_index])

            if isinstance(val, ConcatExpr):
                return val.operands[const_index]

        inst = super().__new__(cls)
        inst.val = val
        inst.index = index
        inst.ctx = ctx

        if inst.dtype.width == 0:
            return ResExpr(Unit())

        return inst

    @property
    def dtype(self):
        val_dtype = self.val.dtype
        if val_dtype is None:
            return None

        if isinstance(self.index, ResExpr):
            return self.val.dtype[self.index.val]

        # TODO: When is this usefull?
        return self.val.dtype[0]


class AttrExpr(Expr):
    def __str__(self):
        return f'{self.val}.{self.attr}'

    def __init__(self, val: Expr, attr: str):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return self.val == other.val and self.attr == other.attr

    def __new__(cls, val: Expr, attr: str):
        const_val = get_contextpr(val)
        if const_val is not None:
            return ResExpr(getattr(const_val, attr))

        inst = super().__new__(cls)
        inst.val = val
        inst.attr = attr

        return inst

    @property
    def dtype(self):
        return getattr(self.val.dtype, self.attr, None)


class ConditionalExpr(Expr):
    def __repr__(self):
        return f'({self.cond} ? {self.operands[0]} : {self.operands[1]})'

    def __init__(self, operands: typing.Sequence[OpType], cond: Expr):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return (self.cond == other.cond and self.operands[0] == other.operands[0]
                and self.operands[1] == other.operands[1])

    def __new__(cls, operands: typing.Sequence[OpType], cond: Expr):
        op1, op2 = operands

        const_cond = get_contextpr(cond)
        if const_cond is not None:
            return op1 if const_cond else op2

        if op1 == op2:
            return op1

        # TODO: Bool should be equivalent to Uint[1]
        if typeof(op1.dtype, (Uint[1], Bool)) and typeof(op2.dtype, (Uint[1], Bool)):
            if cond == op2:
                return BinOpExpr((cond, op1), opc.And)

            const_op1 = get_contextpr(op1)
            if const_op1 is not None:
                if const_op1:
                    return BinOpExpr((cond, op2), opc.Or)
                else:
                    return BinOpExpr((UnaryOpExpr(cond, opc.Not), op2), opc.And)

            const_op2 = get_contextpr(op2)
            if const_op2 is not None:
                if const_op2:
                    return BinOpExpr((UnaryOpExpr(cond, opc.Not), op1), opc.Or)
                else:
                    return BinOpExpr((cond, op1), opc.And)

        inst = super().__new__(cls)
        inst.operands = operands
        inst.cond = cond

        return inst

    @property
    def dtype(self):
        if self.operands[0].dtype.width > self.operands[1].dtype.width:
            return self.operands[0].dtype
        else:
            return self.operands[1].dtype

        # return max([op.dtype for op in self.operands])


@dataclass
class FunctionCall(Expr):
    name: str
    operands: typing.Tuple[OpType]
    keywords: typing.Dict[str, typing.Any] = None
    ret_dtype: PgType = None

    @property
    def dtype(self):
        return self.ret_dtype

    def __str__(self):
        ops = ', '.join([str(op) for op in self.operands])

        kwds = None
        if self.keywords is not None:
            kwds = ', '.join([f'{n}={v}' for n, v in self.keywords.items()])

        if not ops and not kwds:
            sig = ''
        elif not kwds:
            sig = ops
        else:
            sig = ', '.join([ops, kwds])

        return f'{self.name}({sig})'


@dataclass
class CallExpr(Expr):
    func: typing.Any
    args: typing.Tuple[OpType]
    kwds: typing.Dict[str, typing.Any] = field(default_factory=dict)
    params: typing.Dict = field(default_factory=dict)
    pass_eot = True

    @property
    def dtype(self):
        ret = self.params['return']
        if isinstance(ret, tuple):
            ret = Tuple[ret]

        if not self.pass_eot:
            return ret.data

        return ret


@dataclass
class Generator:
    name: str
    func: CallExpr

    @property
    def dtype(self):
        return self.func.dtype


@attr.s(auto_attribs=True)
class GenDone(Expr):
    val: Name

    @property
    def dtype(self):
        return Bool


@attr.s(auto_attribs=True)
class GenInit(Expr):
    val: Name

    @property
    def dtype(self):
        return self.val.dtype


@attr.s(auto_attribs=True)
class GenNext(Expr):
    val: Name

    @property
    def dtype(self):
        return self.val.dtype


@attr.s(auto_attribs=True)
class GenAck(Expr):
    val: Name

    @property
    def dtype(self):
        return self.val.dtype


# Statements


# @attr.s(auto_attribs=True)
@attr.s(auto_attribs=True, kw_only=True, eq=False)
class Statement:
    def __hash__(self):
        return id(self)


@attr.s(auto_attribs=True, eq=False)
class Await(Statement):
    expr: Expr

    def __str__(self):
        return f'(await {str(self.expr)})\n'


@attr.s(auto_attribs=True, eq=False)
class Jump(Statement):
    label: str
    where: typing.Any = None

    def __str__(self):
        if self.where is None:
            return f'->> {str(self.label)}\n'
        else:
            return f'->> {self.label} {self.where}\n'


@attr.s(auto_attribs=True, eq=False)
class ExprStatement(Statement):
    expr: Expr

    def __str__(self):
        return f'{self.expr}\n'


@attr.s(auto_attribs=True, eq=False)
class RegReset(Statement):
    target: Expr

    def __str__(self):
        return f'reset {self.target}\n'


@attr.s(auto_attribs=True, eq=False)
class Assert(Statement):
    test: Expr
    msg: str = None

    def __str__(self):
        return f'{self.test}, "{self.msg}"\n'


def extract_base_targets(target):
    if isinstance(target, ConcatExpr):
        for t in target.operands:
            yield from extract_base_targets(t)
    elif isinstance(target, Name) and isinstance(target.obj, Variable):
        yield target


def extract_partial_targets(target):
    if isinstance(target, SubscriptExpr):
        yield from extract_base_targets(target.val)


@attr.s(auto_attribs=True, eq=False)
class AssignValue(Statement):
    target: Union[str, Name]
    val: Union[str, int, Expr]
    dtype: Union[TypingMeta, None] = None

    def __attrs_post_init__(self):
        for t in extract_base_targets(self.target):
            t.ctx = 'store'

    @property
    def base_targets(self):
        return list(extract_base_targets(self.target))

    @property
    def partial_targets(self):
        return list(extract_partial_targets(self.target))

    def __str__(self):
        return f'{str(self.target)} <= {str(self.val)}\n'


@dataclass
class AssertValue(Statement):
    val: typing.Any


# Blocks


@attr.s(auto_attribs=True, kw_only=True, eq=False)
class BaseBlock(Statement):
    stmts: typing.List = attr.Factory(list)

    def __attrs_post_init__(self):
        if self.stmts is None:
            self.stmts = []

    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        return f'{{\n{textwrap.indent(body, "    ")}}}\n'


@attr.s(auto_attribs=True, kw_only=True, eq=False)
class Module(BaseBlock):
    states: typing.List = attr.Factory(list)
    funcs: typing.List = attr.Factory(list)


@attr.s(auto_attribs=True, eq=False)
class Branch(BaseBlock):
    test: Expr = res_true

    def __str__(self):
        if self.test == res_true and not self.stmts:
            return ''

        if self.test == res_true:
            header = ''
        else:
            header = f'if ({str(self.test)})'

        footer = ''

        body = ''
        for s in self.stmts:
            body += str(s)

        return f'{header}{{\n{textwrap.indent(body, "    ")}}}{footer}'


@attr.s(auto_attribs=True, eq=False)
class LoopBody(BaseBlock):
    state_id: int = None


@attr.s(auto_attribs=True, eq=False)
class HDLBlock(Statement):
    branches: typing.List[Branch] = attr.Factory(list)

    def __init__(self, branches=None):
        if branches is not None:
            branches = [b for b in branches if b.test != res_false]

        super().__init__(branches)

    def add_branch(self, branch: Branch = None):
        if branch is None:
            branch = Branch()

        self.branches.append(branch)
        return branch

    @property
    def has_else(self):
        return self.branches[-1].test == res_true

    def __str__(self):
        sblk = ''
        for i, b in enumerate(self.branches):
            if b.stmts:
                if i > 0:
                    sblk += ' else '

                sblk += str(b)

        sblk += '\n'

        return sblk


@attr.s(auto_attribs=True, eq=False)
class LoopBlock(BaseBlock):
    test: Expr = res_true
    blocking: Expr = False

    def __str__(self):
        return f'do ' + super().__str__() + f'while ({self.test})\n'


@attr.s(auto_attribs=True, eq=False)
class BaseBlockSink(Statement):
    def __str__(self):
        return f'BaseBlockSink'


@attr.s(auto_attribs=True, eq=False)
class ModuleSink(BaseBlockSink):
    def __str__(self):
        return f'ModuleSink'


@attr.s(auto_attribs=True, eq=False)
class BranchSink(BaseBlockSink):
    def __str__(self):
        return f'BranchSink'


@attr.s(auto_attribs=True, eq=False)
class HDLBlockSink(Statement):
    def __str__(self):
        return f'HDLBlockSink'


@attr.s(auto_attribs=True, eq=False)
class LoopBlockSink(BaseBlock):
    def __str__(self):
        return f'LoopBlockSink'


@attr.s(auto_attribs=True, eq=False)
class FuncBlock(Module):
    args: typing.List[Name]
    name: str
    ret_dtype: PgType
    funcs: typing.List = attr.Factory(list)

    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        args = [f'{name}: {val}' for name, val in self.args.items()]
        return f'{self.name}({", ".join(args)}) {{\n{textwrap.indent(body, "    ")}}}\n'


@attr.s(auto_attribs=True, eq=False)
class FuncReturn(Statement):
    func: FuncBlock
    expr: Expr

    def __str__(self):
        return f'return {self.expr}'
