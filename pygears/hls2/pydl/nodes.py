import ast as opc
import typing
import textwrap
from dataclasses import dataclass, field

from pygears.core.port import InPort, OutPort
from pygears.core.gear import InSig, OutSig
from pygears.typing import (Bool, Integer, Queue, Tuple, Uint, Unit, is_type,
                            typeof, Array, Union)
from pygears.typing.base import TypingMeta
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
    opc.Div: operator.__truediv__,
    opc.Eq: operator.__eq__,
    opc.FloorDiv: operator.__floordiv__,
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


def find_sub_dtype(val):
    if isinstance(val, (tuple, list)):
        sub = max(val, key=lambda x: int(getattr(x, 'dtype')))
        return sub.dtype

    return val.dtype


def find_name(node):
    name = getattr(node, 'name', None)
    if name is not None:
        return name

    if hasattr(node, 'val'):
        return find_name(node.val)

    if hasattr(node, 'op'):
        return find_name(node.op)

    return None


class Expr:
    @property
    def dtype(self):
        pass


# Type aliases

PgType = typing.Union[TypingMeta, Unit, int]
OpType = typing.Union[Expr, PgType, str]

# Type definitions


@dataclass
class ResExpr(Expr):
    val: typing.Union[PgType, typing.Sequence, None]

    def __post_init__(self):
        while isinstance(self.val, ResExpr):
            self.val = self.val.val

    def __repr__(self):
        return f'ResExpr({repr(self.val)})'

    def __str__(self):
        return repr(self.val)

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)

        if isinstance(self.val, int):
            return type(Integer(self.val))

        # return type(self.val)

        return None


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
class VariableDef(DefBase):
    pass


@dataclass(frozen=True)
class Variable:
    name: str
    dtype: typing.Union[PgType, typing.Any] = None


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

    @property
    def has_subop(self):
        return isinstance(self.intf, Expr)


@dataclass
class Register(Expr):
    name: str
    val: typing.Union[PgType, Expr] = None
    any_init = False

    @property
    def dtype(self):
        if self.val is None:
            return None
        elif is_type(self.val):
            return self.val
        elif is_type(type(self.val)):
            return type(self.val)

        return self.val.dtype


@dataclass(frozen=True)
class Name(Expr):
    name: str
    obj: typing.Union[Variable, Register]
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
class InterfacePull(Expr):
    intf: Interface

    @property
    def dtype(self):
        return self.intf.dtype

    def __str__(self):
        return f'{str(self.intf)}.data'


@dataclass
class Component(Expr):
    val: Interface
    field: str

    def __repr__(self):
        return f'{self.val.name}.{self.field}'

    @property
    def dtype(self):
        if self.field in ['ready', 'valid']:
            return Bool
        elif self.field == 'data':
            return self.val.dtype

    def __hash__(self):
        return hash(self.val.name)


@dataclass
class InterfaceAck(Expr):
    intf: Interface

    @property
    def dtype(self):
        return Bool


@dataclass
class IntfDef(Expr):
    intf: typing.Union[InPort, OutPort, Expr]
    _name: str = None
    context: str = None

    @property
    def name(self):
        if self._name:
            return self._name
        try:
            return self.intf.basename
        except AttributeError:
            return find_name(self.intf)

    @property
    def dtype(self):
        return find_sub_dtype(self.intf)

    @property
    def has_subop(self):
        return isinstance(self.intf, Expr)


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


# Statements


@dataclass
class RegNextStmt(Expr):
    reg: RegDef
    val: Expr

    @property
    def dtype(self):
        return self.reg.dtype

    @property
    def name(self):
        return find_name(self.reg)


@dataclass
class VariableStmt(Expr):
    variable: VariableDef
    val: Expr

    @property
    def dtype(self):
        return self.variable.dtype

    @property
    def name(self):
        return find_name(self.variable)


@dataclass
class IntfStmt(Expr):
    intf: IntfDef
    val: Expr

    @property
    def dtype(self):
        return self.intf.dtype


@dataclass
class OperandVal(Expr):
    op: typing.Union[VariableDef, RegDef, IntfDef]
    context: str

    @property
    def dtype(self):
        return find_sub_dtype(self.op)


@dataclass
class FunctionCall(Expr):
    name: str
    operands: typing.Tuple[OpType]
    keywords: typing.Dict[str, typing.Any] = None
    ret_dtype: PgType = None

    @property
    def dtype(self):
        return self.ret_dtype


# Inteface operations expressions


@dataclass
class IntfOpExpr(Expr):
    port: typing.Union[IntfDef, str, typing.Sequence]

    @property
    def name(self):
        if isinstance(self.port, str):
            return self.port

        return self.port.name

    @property
    def dtype(self):
        return Bool


@dataclass
class IntfReadyExpr(IntfOpExpr):
    def __hash__(self):
        return hash(self.name)


@dataclass
class IntfValidExpr(IntfOpExpr):
    def __hash__(self):
        return hash(self.name)


# Expressions


@dataclass
class ConcatExpr(Expr):
    def __repr__(self):
        return 'ConcatExpr(' + ', '.join([repr(v) for v in self.operands]) + ')'

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


@dataclass
class CastExpr(Expr):
    operand: OpType
    cast_to: PgType

    def __post_init__(self):
        if isinstance(self.operand, ConcatExpr) and typeof(
                self.cast_to, (Array, Tuple, Queue, Union)):
            cast_ops = [
                CastExpr(op, cast_t) if op.dtype != cast_t else op
                for op, cast_t in zip(self.operand.operands, self.cast_to)
            ]
            self.operand = ConcatExpr(cast_ops)

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


@dataclass
class ArrayOpExpr(Expr):
    array: OpType
    operator: str

    def __str__(self):
        return f'{OPMAP[self.operator]}({str(self.array)})'

    @property
    def dtype(self):
        return Uint[1]


class SubscriptExpr(Expr):
    def __repr__(self):
        return f'{type(self).__name__}(val={repr(self.val)}, index={repr(self.index)})'

    def __str__(self):
        return f'{self.val}[{self.index}]'

    def __init__(self, val: Expr, index: Expr):
        pass

    def __new__(cls, val: Expr, index: Expr):
        if isinstance(index, ResExpr):
            if isinstance(val, ResExpr):
                return ResExpr(val.val[index.val])

            if isinstance(val, ConcatExpr):
                return val.operands[index.val]

        inst = super().__new__(cls)
        inst.val = val
        inst.index = index

        if typeof(inst.dtype, Unit):
            return ResExpr(Unit())

        return inst

    @property
    def dtype(self):
        if isinstance(self.index, ResExpr):
            return self.val.dtype[self.index.val]

        return self.val.dtype[0]


@dataclass
class AttrExpr(Expr):
    val: Expr
    attr: str

    def __str__(self):
        return f'{self.val}.{self.attr}'

    def __init__(self, val: Expr, attr: str):
        pass

    def __new__(cls, val: Expr, attr: str):
        if isinstance(val, ResExpr):
            return ResExpr(getattr(val.val, attr))

        inst = super().__new__(cls)
        inst.val = val
        inst.attr = attr

        return inst

    @property
    def dtype(self):
        return getattr(self.val.dtype, self.attr)

    # @property
    # def dtype(self):
    #     return self.get_attr_dtype(self.val.dtype)

    # def get_attr_dtype(self, val_type):
    #     for attr in self.attr:
    #         if typeof(val_type, Tuple):
    #             val_type = val_type[attr]
    #         elif typeof(val_type, Queue):
    #             try:
    #                 val_type = val_type[attr]
    #             except KeyError:
    #                 val_type = self.get_attr_dtype(val_type[0])
    #         else:
    #             val_type = getattr(val_type, attr, None)
    #     return val_type


class ConditionalExpr(Expr):
    def __repr__(self):
        return f'({self.cond} ? {self.operands[0]} : {self.operands[1]})'

    def __init__(self, operands: typing.Sequence[OpType], cond: Expr):
        pass

    def __new__(cls, operands: typing.Sequence[OpType], cond: Expr):
        op1, op2 = operands

        if isinstance(cond, ResExpr):
            return op1 if cond.val else op2

        if op1 == op2:
            return op1

        if isinstance(op1, ResExpr) and not op1.val:
            return BinOpExpr((UnaryOpExpr(cond, opc.Not), op2), opc.And)

        if isinstance(op2, ResExpr) and not op2.val:
            return BinOpExpr((cond, op1), opc.And)

        inst = super().__new__(cls)
        inst.operands = operands
        inst.cond = cond

        return inst

    @property
    def dtype(self):
        return max([op.dtype for op in self.operands])


@dataclass
class BreakExpr(Expr):
    pass


# Conditions


def is_container(block):
    return isinstance(block, (ContainerBlock, CombBlock))


def is_intftype(block):
    return isinstance(block, (IntfBlock, IntfLoop))


@dataclass
class SubConditions:
    expr: OpType = None
    operator: str = None


@dataclass
class CycleSubCond(SubConditions):
    pass


@dataclass
class ExitSubCond(SubConditions):
    pass


@dataclass
class BothSubCond(SubConditions):
    pass


# Blocks


@dataclass
class Block:
    # TODO : newer versions of Python will not need the string
    stmts: typing.List[typing.Union['Block', Expr]]

    # @property
    # def in_cond(self):
    #     pass

    # @property
    # def cycle_cond(self):
    #     pass

    # @property
    # def exit_cond(self):
    #     pass


@dataclass
class BaseLoop(Block):
    multicycle: typing.List[Expr]

    @property
    def cycle_cond(self):
        return CycleSubCond()


@dataclass
class IntfBlock(Block):
    intfs: typing.List[Interface]

    # @property
    # def in_cond(self):
    #     return self.intfs[0]

    # @property
    # def cycle_cond(self):
    #     return CycleSubCond()

    # @property
    # def exit_cond(self):
    #     return ExitSubCond()


@dataclass
class IntfLoop(BaseLoop):
    intf: IntfDef


@dataclass
class IfBlock(Block):
    test: Expr

    def __str__(self):
        header = f'if {str(self.test)}:'
        body = ''
        for s in self.stmts:
            body += str(s)

        return f'{header}\n{textwrap.indent(body, "    ")}'


@dataclass
class ElseBlock(Block):
    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        return f'else:\n{textwrap.indent(body, "    ")}'



@dataclass
class ContainerBlock(Block):
    def __str__(self):
        body = ''
        for i, s in enumerate(self.stmts):
            ss = str(s)
            if i > 1 and isinstance(s, IfBlock):
                body += 'el'

            body += ss

        return body

    # stmts: typing.List[Block]

    # @property
    # def cycle_cond(self):
    #     from .conditions_utils import CycleCond
    #     return CycleCond(self.id)

    # @property
    # def exit_cond(self):
    #     from .conditions_utils import ExitCond
    #     return ExitCond(self.id)


@dataclass
class CombBlock(ContainerBlock):
    pass


@dataclass
class Loop(BaseLoop):
    test: Expr


@dataclass
class Statement:
    expr: Expr


@dataclass
class Return(Statement):
    pass


@dataclass
class Yield(Statement):
    ports: typing.List[IntfDef]

    def __str__(self):
        if len(self.ports) == 1:
            return f'{str(self.ports[0])} <= {self.expr.val[0]}\n'
        else:
            assigns = ''
            for p, e in zip(self.ports, self.expr.vals):
                assigns += f'{str(p)} <= {e}\n'

            return assigns


@dataclass
class Assign(Statement):
    var: Variable


@dataclass
class Assert(Statement):
    msg: str


@dataclass
class Function(Block):
    name: str
    args: typing.List[str]
    ret_dtype: PgType


@dataclass
class Module(Block):
    pass


class PydlPrinter:
    def __init__(self, indent=2):
        self.indent = 0
        self.indent_incr = indent
        self.msg = ''
        self.fieldname = None

    def enter_block(self):
        self.indent += self.indent_incr

    def exit_block(self):
        self.indent -= self.indent_incr

    def write_line(self, line):
        self.msg += f'{" "*self.indent}{line}\n'

    @property
    def field_hdr(self):
        if self.fieldname:
            return f'{self.fieldname}='
        else:
            return ''

    def visit_OperandVal(self, node):
        # if isinstance(node, expr.RegDef):
        #     return expr.OperandVal(var, 'reg')

        # if isinstance(var, expr.VariableDef):
        #     return expr.OperandVal(var, 'v')

        if type(node.op).__name__ == "IntfDef":
            return self.write_line(
                f'{self.field_hdr}"{node.op.intf.basename}"')

    def visit_IntfDef(self, node):
        return self.write_line(f'{self.field_hdr}"{node.intf.basename}"')

    def generic_visit(self, node):
        if hasattr(node, 'stmts'):
            if node.stmts:
                self.write_line(
                    f'{self.field_hdr}{node.__class__.__name__}[{node.id}](')
                self.enter_block()
                for s in node.stmts:
                    self.visit(s)
                self.exit_block()
                self.write_line(')')
            else:
                self.write_line(
                    f'{self.field_hdr}{node.__class__.__name__}[{node.id}]')

        elif hasattr(node, '__dataclass_fields__'):
            self.write_line(f'{self.field_hdr}{node.__class__.__name__}{{')
            self.enter_block()
            for fn in node.__dataclass_fields__:
                self.fieldname = fn
                self.visit(getattr(node, fn))
            self.fieldname = None
            self.exit_block()
            self.write_line('}')
        elif isinstance(node, (tuple, list)):
            self.write_line(f'{self.field_hdr}(')
            self.fieldname = None
            self.enter_block()
            for elem in node:
                self.visit(elem)
            self.exit_block()
            self.write_line(')')
        else:
            self.write_line(f'{self.field_hdr}{node}')

        return self.msg

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)


def pformat(node):
    return PydlPrinter().visit(node)
