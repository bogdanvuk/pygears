import ast as opc
import inspect
import attr
import typing
import textwrap
from dataclasses import dataclass, field

from pygears.typing.base import TypingMeta
from functools import reduce
from pygears.core.port import InPort, OutPort
from pygears.core.gear import InSig, OutSig
from pygears.typing import (Bool, Integer, Queue, Tuple, Uint, is_type, typeof, Array, Union, Unit)
# from .ast.utils import get_property_type
import operator

BOOLEAN_OPERATORS = {opc.BitOr, opc.BitAnd, opc.BitXor, opc.Invert, opc.Not, opc.And, opc.Or}
BIN_OPERATORS = [opc.Eq, opc.Gt, opc.GtE, opc.Lt, opc.LtE, opc.NotEq, opc.And, opc.Or]
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
    return PYOPMAP[op](*(p.val for p in operands))


def bin_op_reduce(intfs, func, op, dflt=None):
    if not intfs:
        return dflt

    intf1 = func(intfs[0])

    if len(intfs) == 1:
        return intf1
    else:
        return BinOpExpr([intf1, bin_op_reduce(intfs[1:], func, op, dflt=dflt)], op)


def find_sub_dtype(val):
    if isinstance(val, (tuple, list)):
        sub = max(val, key=lambda x: int(getattr(x, 'dtype')))
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


@attr.s(auto_attribs=True, kw_only=True)
class Expr:
    @property
    def dtype(self):
        pass


# Type aliases

PgType = typing.Union[TypingMeta, Unit, int]
OpType = typing.Union[Expr, PgType, str]

# Type definitions


class ResExpr(Expr):
    def __new__(cls, val):
        if isinstance(val, Expr):
            return val

        inst = super().__new__(cls)
        inst.val = val

        return inst

    def __init__(self, val):
        super().__init__()

    def __eq__(self, other):
        if not isinstance(other, ResExpr):
            return False

        return self.val == other.val

    def __repr__(self):
        return f'ResExpr({repr(self.val)})'

    def __str__(self):
        return str(self.val)

    @property
    def dtype(self):
        # if is_type(type(self.val)):
        #     return type(self.val)

        if not is_type(type(self.val)) and isinstance(self.val, int):
            return type(Integer(self.val))

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
            return self.val.dtype


@attr.s(auto_attribs=True)
class Await(Expr):
    expr: Expr = None
    in_await: Expr = res_true
    exit_await: Expr = res_true

    @property
    def dtype(self):
        if self.expr is None:
            return None

        return self.expr.dtype

    def __str__(self):
        if self.in_await != res_true:
            footer = f'(in-await {self.in_await})'

        if self.exit_await != res_true:
            footer = f'(exit-await {self.exit_await})'

        if self.expr:
            return f'{str(self.expr)} {footer}'
        else:
            return footer


@attr.s(auto_attribs=True)
class InterfacePull(Expr):
    intf: Interface

    @property
    def in_await(self):
        return Component(self.intf, 'valid')

    @in_await.setter
    def in_await(self, val):
        pass

    @property
    def dtype(self):
        return self.intf.obj.dtype

    def __str__(self):
        return f'{str(self.intf)}.data'


@attr.s(auto_attribs=True)
class InterfaceReady(Expr):
    intf: Interface

    @property
    def exit_await(self):
        return Component(self.intf, 'ready')

    @exit_await.setter
    def exit_await(self, val):
        pass

    @property
    def dtype(self):
        return Bool

    def __str__(self):
        return f'{str(self.intf)}.ready'


@dataclass
class InterfaceAck(Expr):
    intf: Interface

    @property
    def dtype(self):
        return Bool


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
            if all(is_type(v.dtype) for v in operands):
                return ResExpr(Tuple[tuple(v.dtype for v in operands)](tuple(v.val for v in operands)))
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

        if operator == opc.Not and isinstance(operand, UnaryOpExpr) and operand.operator == opc.Not:
            return operand.operand

        inst = super().__new__(cls)
        inst.operand = operand
        inst.operator = operator
        return inst

    @property
    def dtype(self):
        return Uint[1] if (self.operand == opc.Not) else self.operand.dtype


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


class BinOpExpr(Expr):
    def __repr__(self):
        try:
            return f'{type(self).__name__}(operands={repr(self.operands)}, operator={self.operator.__name__})'
        except:
            return f'{type(self).__name__}(operands={repr(self.operands)}, operator={self.operator})'

    def __str__(self):
        return f'({self.operands[0]} {OPMAP[self.operator]} {self.operands[1]})'

    def __init__(self, operands: typing.Tuple[OpType], operator):
        pass

    def __new__(cls, operands: typing.Tuple[OpType], operator):
        op1, op2 = operands
        if isinstance(op1, ResExpr) and isinstance(op2, ResExpr):
            return ResExpr(opex(operator, op1, op2))

        if operator == opc.And:
            if isinstance(op1, ResExpr):
                return op2 if op1.val else op1
            if isinstance(op2, ResExpr):
                return op1 if op2.val else op2

        elif operator == opc.Or:
            if isinstance(op1, ResExpr):
                return op1 if op1.val else op2
            if isinstance(op2, ResExpr):
                return op2 if op2.val else op1

        elif operator in (opc.RShift, opc.LShift):
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
        return f'{type(self).__name__}(val={repr(self.val)}, index={repr(self.index)})'

    def __str__(self):
        return f'{self.val}[{self.index}]'

    def __init__(self, val: Expr, index: Expr):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return self.val == other.val and self.index == other.index

    def __new__(cls, val: Expr, index: Expr):
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

        const_op1 = get_contextpr(op1)
        if const_op1 is not None and not const_op1:
            return BinOpExpr((UnaryOpExpr(cond, opc.Not), op2), opc.And)

        const_op2 = get_contextpr(op1)
        if const_op1 is not None and not const_op2:
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
    in_await: Expr = res_true
    exit_await: Expr = res_true

    def __hash__(self):
        return id(self)


@attr.s(auto_attribs=True, eq=False)
class ExprStatement(Statement):
    expr: Expr

    @property
    def in_await(self):
        if isinstance(self.expr, Await):
            return self.expr.in_await

        if isinstance(self.expr, ConcatExpr):
            return bin_op_reduce(
                list(op.in_await for op in self.expr.operands if isinstance(op, Await)),
                lambda op: op, opc.And, res_true)

        return res_true

    @in_await.setter
    def in_await(self, val):
        pass

    @property
    def exit_await(self):
        if isinstance(self.expr, Await):
            return self.expr.exit_await

        return res_true

    @exit_await.setter
    def exit_await(self, val):
        pass

    def __str__(self):
        return f'{self.expr}\n'


@attr.s(auto_attribs=True, eq=False)
class Assert(Statement):
    test: Expr
    msg: str = None


def extract_base_targets(target):
    if isinstance(target, SubscriptExpr):
        yield from extract_base_targets(target.val)
    elif isinstance(target, ConcatExpr):
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
    in_await = attr.ib()
    exit_await = attr.ib()
    dtype: Union[TypingMeta, None] = None

    def __attrs_post_init__(self):
        for t in extract_base_targets(self.target):
            t.ctx = 'store'

    @property
    def in_await(self):
        if isinstance(self.val, Await):
            return self.val.in_await

        if isinstance(self.val, ConcatExpr):
            return bin_op_reduce(
                list(op.in_await for op in self.val.operands if isinstance(op, Await)),
                lambda op: op, opc.And, res_true)

        return res_true

    @in_await.setter
    def in_await(self, val):
        pass

    @property
    def exit_await(self):
        if isinstance(self.val, Await):
            return self.val.exit_await

        return res_true

    @exit_await.setter
    def exit_await(self, val):
        pass

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
    stmts: typing.List = None

    def __attrs_post_init__(self):
        if self.stmts is None:
            self.stmts = []

    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        return f'{{\n{textwrap.indent(body, "    ")}}}\n'


@attr.s(auto_attribs=True, eq=False)
class HDLBlock(BaseBlock):
    test: Expr = None
    in_cond: Expr = res_true
    exit_cond: Expr = res_true

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        if self.test is not None:
            self.in_cond = self.test

    def __str__(self):
        body = ''

        if self.in_cond == res_true:
            header = ''
        else:
            header = f'(if {str(self.in_cond)})'

        footer = ''
        if self.exit_cond != res_true:
            footer = f' (exit: {str(self.exit_cond)})'

        for s in self.stmts:
            body += str(s)

        if not header and body.count('\n') == 1:
            return f'{body[:-1]}{footer}\n'

        return f'{header}{{\n{textwrap.indent(body, "    ")}}}{footer}\n'


@attr.s(auto_attribs=True, eq=False)
class LoopBlock(HDLBlock):
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        if self.test is not None:
            self.exit_cond = UnaryOpExpr(self.test, opc.Not)


@attr.s(auto_attribs=True, eq=False)
class IfElseBlock(HDLBlock):
    def __str__(self):
        return f'IfElse {super().__str__()}'


@attr.s(auto_attribs=True, eq=False)
class CombBlock(BaseBlock):
    funcs: typing.List = attr.Factory(list)


@attr.s(auto_attribs=True, eq=False)
class FuncBlock(BaseBlock):
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
