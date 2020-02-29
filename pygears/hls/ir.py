import ast as opc
import typing
import textwrap
from dataclasses import dataclass, field

from pygears.typing.base import TypingMeta
from functools import reduce
from pygears.core.port import InPort, OutPort
from pygears.core.gear import InSig, OutSig
from pygears.typing import (Bool, Integer, Queue, Tuple, Uint, is_type, typeof,
                            Array, Union, Unit)
import operator

BOOLEAN_OPERATORS = {
    opc.BitOr, opc.BitAnd, opc.BitXor, opc.Invert, opc.Not, opc.And, opc.Or
}
BIN_OPERATORS = [
    opc.Not, opc.Eq, opc.Gt, opc.GtE, opc.Lt, opc.LtE, opc.NotEq, opc.And,
    opc.Or
]
EXTENDABLE_OPERATORS = [
    opc.Add, opc.Sub, opc.Mult, opc.Div, opc.Mod, opc.Pow, opc.LShift,
    opc.RShift, opc.BitOr, opc.BitAnd, opc.BitXor, opc.Div, opc.Invert, opc.Not
]
OPMAP = {
    opc.Add: '+',
    opc.Sub: '-',
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
    opc.BitOr: operator.__and__,
    opc.Div: operator.__truediv__,
    opc.Eq: operator.__eq__,
    opc.Gt: operator.__gt__,
    opc.GtE: operator.__ge__,
    opc.FloorDiv: operator.__floordiv__,
    opc.Lt: operator.__lt__,
    opc.LtE: operator.__le__,
    opc.LShift: operator.__lshift__,
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


def create_oposite(expr):
    if isinstance(expr, UnaryOpExpr) and expr.operator == opc.Not:
        return expr.operand

    return UnaryOpExpr(expr, opc.Not)


def binary_expr(expr1, expr2, operator):
    if expr1 is None:
        return expr2

    if expr2 is None:
        return expr1

    if expr1 is None and expr2 is None:
        return None

    return BinOpExpr((expr1, expr2), operator)


def and_expr(expr1, expr2):
    return binary_expr(expr1, expr2, opc.And)


def or_expr(expr1, expr2):
    return binary_expr(expr1, expr2, opc.Or)


def bin_op_reduce(intfs, func, op):
    intf1 = func(intfs[0])

    if len(intfs) == 1:
        return intf1
    else:
        return BinOpExpr([intf1, bin_op_reduce(intfs[1:], func, op)], op)


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


def is_constexpr(node):
    if isinstance(node, ResExpr):
        return True

    if isinstance(node, Variable) and node.val != None:
        return True

    return False


def get_contextpr(node):
    if isinstance(node, ResExpr):
        return node.val

    if isinstance(node, Name):
        obj = node.obj
        if isinstance(obj, Variable) and obj.val is not None:
            return obj.val

    return None


class Expr:
    in_cond: typing.Any = None
    exit_cond: typing.Any = None

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
        if is_type(type(self.val)):
            return type(self.val)

        if isinstance(self.val, int):
            return type(Integer(self.val))

        # return type(self.val)

        return None


res_true = ResExpr(Bool(True))
res_false = ResExpr(Bool(True))


@dataclass
class TupleExpr(Expr):
    val: typing.Sequence

    def __getitem__(self, key):
        return self.val[key]


@dataclass
class DefBase(Expr):
    val: typing.Union[PgType, Expr]
    name: str

    @property
    def dtype(self):
        if self.val is None:
            return None
        elif is_type(self.val):
            return self.val
        elif is_type(type(self.val)):
            return type(self.val)

        return self.val.dtype


@dataclass
class RegDef(DefBase):
    pass


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


@dataclass
class Name(Expr):
    name: str
    obj: Variable
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


@dataclass
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


@dataclass
class InterfacePull(Expr):
    intf: Interface

    @property
    def in_cond(self):
        return Component(self.intf, 'valid')

    @property
    def dtype(self):
        return self.intf.obj.dtype

    def __str__(self):
        return f'{str(self.intf)}.data'


@dataclass
class InterfaceReady(Expr):
    intf: Interface

    @property
    def exit_cond(self):
        return Component(self.intf, 'ready')

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
class SignalDef(Expr):
    sig: typing.Union[InSig, OutSig]
    context: str = None

    @property
    def name(self):
        return self.sig.name

    @property
    def dtype(self):
        return Uint[self.sig.width]


@dataclass
class SignalStmt(Expr):
    variable: SignalDef
    val: Expr

    @property
    def dtype(self):
        return self.variable.dtype

    @property
    def name(self):
        return self.variable.name


# Expressions


@dataclass
class ConcatExpr(Expr):
    def __repr__(self):
        return 'ConcatExpr(' + ', '.join([repr(v)
                                          for v in self.operands]) + ')'

    def __str__(self):
        return '(' + ', '.join([str(v) for v in self.operands]) + ')'

    def __init__(self, operands: typing.Sequence[Expr]):
        pass

    def __new__(cls, operands: typing.Sequence[Expr]):
        if all(isinstance(v, ResExpr) for v in operands):
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

    def __new__(cls, operand, operator):
        if isinstance(operand, ResExpr):
            return ResExpr(opex(operator, operand))

        if operator == opc.Not and isinstance(operand, BinOpExpr):
            if operand.operator == opc.Eq:
                return BinOpExpr(operand.operands, opc.NotEq)

            if operand.operator == opc.NotEq:
                return BinOpExpr(operand.operands, opc.Eq)

        if operator == opc.Not and isinstance(
                operand, UnaryOpExpr) and operand.operator == opc.Not:
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

    def __new__(cls, operand, cast_to):
        if isinstance(cast_to, ResExpr):
            cast_to = cast_to.val

        if operand.dtype == cast_to:
            return operand

        if isinstance(operand, ConcatExpr) and typeof(
                cast_to, (Array, Tuple, Queue, Union)):
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

    def __new__(cls, start: OpType, stop: OpType, step: OpType):
        if isinstance(start, ResExpr) and isinstance(
                stop, ResExpr) and isinstance(step, ResExpr):
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

        inst = super().__new__(cls)
        inst.operands = operands
        inst.operator = operator
        return inst

    @property
    def dtype(self):
        if self.operator in BIN_OPERATORS:
            return Uint[1]

        if (self.operator in (opc.LShift, opc.RShift)) and isinstance(
                self.operands[1], ResExpr):
            op2 = self.operands[1].val
        else:
            op2 = self.operands[1].dtype

        res_t = eval(f'op1 {OPMAP[self.operator]} op2', {
            'op1': self.operands[0].dtype,
            'op2': op2
        })

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

    def __new__(cls, array: Expr, operator):
        if isinstance(array, ResExpr):
            return ResExpr(
                reduce(PYOPMAP[operator], array.val, REDUCE_INITIAL[operator]))

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

        if typeof(inst.dtype, Unit):
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
        return max([op.dtype for op in self.operands])


@dataclass
class FunctionCall(Expr):
    name: str
    operands: typing.Tuple[OpType]
    keywords: typing.Dict[str, typing.Any] = None
    ret_dtype: PgType = None

    @property
    def dtype(self):
        return self.ret_dtype


@dataclass
class GenCallExpr(Expr):
    func: typing.Any
    args: typing.Tuple[OpType]
    kwds: typing.Dict[str, typing.Any]
    params: typing.Dict
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
    func: GenCallExpr

    @property
    def dtype(self):
        return self.func.dtype


@dataclass
class GenLive(Expr):
    val: Name

    @property
    def dtype(self):
        return Bool


@dataclass
class GenDone(Expr):
    val: Name

    @property
    def dtype(self):
        return Bool


@dataclass
class GenNext(Expr):
    val: Name

    @property
    def dtype(self):
        return self.val.dtype


# Statements


class Statement:
    in_block: bool = False
    out_block: bool = False


@dataclass
class Assert(Statement):
    msg: str


@dataclass
class Await(Statement):
    expr: Expr

    @property
    def dtype(self):
        return self.expr.dtype


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


@dataclass
class AssignValue(Statement):
    target: Union[str, Name]
    val: Union[str, int, Expr]
    dtype: Union[TypingMeta, None] = None
    opt_in_cond: Expr = res_true

    def __post_init__(self):
        for t in extract_base_targets(self.target):
            t.ctx = 'store'

    @property
    def in_cond(self):
        in_cond = self.val.in_cond
        return in_cond if in_cond is not None else res_true

    @property
    def exit_cond(self):
        exit_cond = self.val.exit_cond
        return exit_cond if exit_cond is not None else res_true

    @property
    def base_targets(self):
        return list(extract_base_targets(self.target))

    @property
    def partial_targets(self):
        return list(extract_partial_targets(self.target))

    def __str__(self):

        footer = ''
        if self.exit_cond != res_true:
            footer = f' (exit: {str(self.exit_cond)})'

        return f'{str(self.target)} <= {str(self.val)}{footer}\n'


@dataclass
class AssertValue(Statement):
    val: typing.Any


# Blocks


@dataclass
class BaseBlock:
    # TODO : newer versions of Python will not need the string
    stmts: typing.List[typing.Union[AssignValue, 'HDLBlock']]

    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        return f'{{\n{textwrap.indent(body, "    ")}}}\n'


@dataclass
class HDLBlock(BaseBlock):
    in_cond: Expr = res_true
    opt_in_cond: Expr = res_true
    exit_cond: Expr = res_true

    def __str__(self):
        body = ''
        conds = {
            'in': self.in_cond,
            'opt_in': self.opt_in_cond,
        }
        header = []
        for name, val in conds.items():
            if val != res_true:
                header.append(f'{name}: {str(val)}')

        if header:
            header = '(' + ', '.join(header) + ') '
        else:
            header = ''

        footer = ''
        if self.exit_cond != res_true:
            footer = f' (exit: {str(self.exit_cond)})'

        for s in self.stmts:
            body += str(s)

        if not header and body.count('\n') == 1:
            return f'{body[:-1]}{footer}\n'

        return f'{header}{{\n{textwrap.indent(body, "    ")}}}{footer}\n'


@dataclass
class IntfBlock(HDLBlock):
    intfs: typing.List = field(default_factory=list)

    def __post_init__(self):
        self.in_cond = bin_op_reduce(self.intfs,
                                     lambda i: Component(i, 'valid'), opc.And)

    def close(self):
        for i in self.intfs:
            self.stmts.append(
                AssignValue(target=Component(i, 'ready'), val=res_true))


@dataclass
class LoopBlock(HDLBlock):
    test: Expr = None

    def __post_init__(self):
        if self.test is not None:
            self.exit_cond = UnaryOpExpr(self.test, opc.Not)
            self.opt_in_cond = self.test


@dataclass
class IfElseBlock(HDLBlock):
    def __str__(self):
        return f'IfElse {super().__str__()}'


@dataclass
class CombBlock(BaseBlock):
    funcs: typing.List = field(default_factory=list)


@dataclass
class FuncBlock(BaseBlock):
    args: typing.List[Name]
    name: str
    ret_dtype: PgType
    in_cond: Expr = res_true
    opt_in_cond: Expr = res_true
    funcs: typing.List = field(default_factory=list)

    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        args = [f'{name}: {val}' for name, val in self.args.items()]
        return f'{self.name}({", ".join(args)}) {{\n{textwrap.indent(body, "    ")}}}\n'


@dataclass
class FuncReturn:
    func: FuncBlock
    expr: Expr

    def __str__(self):
        return f'return {self.expr}'
