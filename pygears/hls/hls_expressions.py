import ast
import typing
from dataclasses import dataclass

from pygears.core.port import InPort, OutPort
from pygears.typing import (Bool, Integer, Queue, Tuple, Uint, Unit, is_type,
                            typeof)
from pygears.typing.base import TypingMeta

BOOLEAN_OPERATORS = {'|', '&', '^', '~', '!', '&&', '||'}
BIN_OPERATORS = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
EXTENDABLE_OPERATORS = [
    '+', '-', '*', '/', '%', '**', '<<', '>>', '|', '&', '^', '/', '~', '!'
]
OPMAP = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
    ast.Pow: '**',
    ast.LShift: '<<',
    ast.RShift: '>>',
    ast.BitOr: '|',
    ast.BitAnd: '&',
    ast.BitXor: '^',
    ast.FloorDiv: '/',
    ast.Invert: '~',
    ast.Not: '!',
    ast.UAdd: '+',
    ast.USub: '-',
    ast.Eq: '==',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.NotEq: '!=',
    ast.And: '&&',
    ast.Or: '||'
}


def create_oposite(expr):
    if isinstance(expr, UnaryOpExpr) and expr.operator == '!':
        return expr.operand

    return UnaryOpExpr(expr, '!')


def binary_expr(expr1, expr2, operator):
    if expr1 is None:
        return expr2

    if expr2 is None:
        return expr1

    if expr1 is None and expr2 is None:
        return None

    return BinOpExpr((expr1, expr2), operator)


def and_expr(expr1, expr2):
    return binary_expr(expr1, expr2, '&&')


def or_expr(expr1, expr2):
    return binary_expr(expr1, expr2, '||')


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


@dataclass
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

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)

        if self.val is not None:
            return Integer(self.val)

        return None


@dataclass
class DefBase(Expr):
    val: typing.Union[PgType, Expr]
    name: str

    @property
    def dtype(self):
        if is_type(self.val):
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
class ReturnStmt:
    val: Expr


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
    operands: typing.Tuple[OpType]
    name: str
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
    operands: typing.Sequence[OpType]

    @property
    def dtype(self):
        return Tuple[tuple(op.dtype for op in self.operands)]


@dataclass
class UnaryOpExpr(Expr):
    operand: OpType
    operator: str

    @property
    def dtype(self):
        return Uint[1] if (self.operand == '!') else self.operand.dtype


@dataclass
class CastExpr(Expr):
    operand: OpType
    cast_to: PgType

    @property
    def dtype(self):
        return self.cast_to


@dataclass
class BinOpExpr(Expr):
    operands: typing.Tuple[OpType]
    operator: str

    @property
    def dtype(self):
        if self.operator in BIN_OPERATORS:
            return Uint[1]

        res_t = eval(f'op1 {self.operator} op2', {
            'op1': self.operands[0].dtype,
            'op2': self.operands[1].dtype
        })

        if isinstance(res_t, bool):
            return Uint[1]

        return res_t


@dataclass
class ArrayOpExpr(Expr):
    array: OpType
    operator: str

    @property
    def dtype(self):
        return Uint[1]


@dataclass
class SubscriptExpr(Expr):
    val: OpType
    index: typing.Union[Expr, int, slice]

    @property
    def dtype(self):
        if isinstance(self.index, OperandVal):
            return self.val.dtype[0]

        if not isinstance(self.index, slice):
            return self.val.dtype[self.index]

        return self.val.dtype.__getitem__(self.index)

    def __hash__(self):
        return hash(find_name(self.val))


@dataclass
class AttrExpr(Expr):
    val: Expr
    attr: typing.List[typing.Union[int, str]]

    @property
    def dtype(self):
        return self.get_attr_dtype(self.val.dtype)

    def get_attr_dtype(self, val_type):
        for attr in self.attr:
            if typeof(val_type, Tuple):
                val_type = val_type[attr]
            elif typeof(val_type, Queue):
                try:
                    val_type = val_type[attr]
                except KeyError:
                    val_type = self.get_attr_dtype(val_type[0])
            else:
                val_type = getattr(val_type, attr, None)
        return val_type


@dataclass
class ConditionalExpr(Expr):
    operands: typing.Sequence[OpType]
    cond: Expr

    @property
    def dtype(self):
        return max([op.dtype for op in self.operands])


@dataclass
class AssertExpr(Expr):
    test: Expr
    msg: str


@dataclass
class BreakExpr(Expr):
    pass
