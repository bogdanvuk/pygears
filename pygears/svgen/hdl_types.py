from dataclasses import dataclass
import typing as pytypes

from pygears.typing import Tuple, typeof, Uint, Queue, is_type, Bool
from functools import reduce

bin_operators = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
extendable_operators = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]


def find_exit_cond(statements):
    for stmt in reversed(statements):
        if hasattr(stmt, 'exit_cond'):
            stmt_cond = stmt.exit_cond
            if stmt_cond is not None:
                return stmt_cond

    return None


def find_cycle_cond(statements):
    cond = []
    for stmt in statements:
        # if hasattr(stmt, 'cycle_cond') and not stmt.in_cond:
        if hasattr(stmt, 'cycle_cond'):
            stmt_cond = stmt.cycle_cond
            if stmt_cond is not None:
                cond.append(stmt_cond)

    return reduce(and_expr, cond, None)


def and_expr(expr1, expr2):
    if expr1 is None:
        return expr2
    elif expr2 is None:
        return expr1
    elif expr1 is None and expr2 is None:
        return None
    else:
        return BinOpExpr((expr1, expr2), '&&')


# Expressions


class Expr:
    @property
    def dtype(self):
        pass


class IntfReadyExpr(Expr, pytypes.NamedTuple):
    @property
    def dtype(self):
        return Bool


class ResExpr(Expr, pytypes.NamedTuple):
    val: pytypes.Any

    @property
    def dtype(self):
        return type(self.val)


class RegDef(Expr, pytypes.NamedTuple):
    val: pytypes.Any
    name: str

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)
        else:
            return self.val.dtype


class RegNextStmt(Expr, pytypes.NamedTuple):
    reg: RegDef
    val: Expr

    @property
    def dtype(self):
        return self.reg.dtype


class RegVal(Expr, pytypes.NamedTuple):
    reg: RegDef
    name: str

    @property
    def dtype(self):
        return self.reg.dtype


class VariableDef(pytypes.NamedTuple):
    val: pytypes.Any
    name: str

    @property
    def dtype(self):
        return self.val.dtype


class VariableStmt(Expr, pytypes.NamedTuple):
    variable: VariableDef
    val: Expr

    @property
    def dtype(self):
        return self.variable.dtype


class VariableVal(Expr, pytypes.NamedTuple):
    variable: VariableDef
    name: str

    @property
    def dtype(self):
        return self.variable.dtype


class IntfExpr(Expr, pytypes.NamedTuple):
    intf: pytypes.Any
    context: str = None

    @property
    def name(self):
        return self.intf.basename

    @property
    def dtype(self):
        return self.intf.dtype


class ConcatExpr(Expr, pytypes.NamedTuple):
    operands: tuple

    @property
    def dtype(self):
        return Tuple[tuple(op.dtype for op in self.operands)]


class UnaryOpExpr(Expr, pytypes.NamedTuple):
    operand: Expr
    operator: str

    @property
    def dtype(self):
        return Uint[1] if (self.operand is '!') else self.operand.dtype


class BinOpExpr(Expr, pytypes.NamedTuple):
    operands: tuple
    operator: str

    @property
    def dtype(self):
        if self.operator in bin_operators:
            return Uint[1]

        t = eval(f'op1 {self.operator} op2', {
            'op1': self.operands[0].dtype,
            'op2': self.operands[1].dtype
        })
        if isinstance(t, bool):
            return Uint[1]
        else:
            return t


class ArrayOpExpr(Expr, pytypes.NamedTuple):
    array: Expr
    operator: str

    @property
    def dtype(self):
        return Uint[1]


class SubscriptExpr(Expr, pytypes.NamedTuple):
    val: Expr
    index: pytypes.Any

    @property
    def dtype(self):
        if not isinstance(self.index, slice):
            return self.val.dtype[self.index]
        else:
            return self.val.dtype.__getitem__(self.index)


class AttrExpr(Expr, pytypes.NamedTuple):
    val: Expr
    attr: list

    @property
    def dtype(self):
        return self.get_attr_dtype(self.val.dtype)

    def get_attr_dtype(self, t):
        for attr in self.attr:
            if typeof(t, Tuple):
                t = t[attr]
            elif typeof(t, Queue):
                try:
                    t = t[attr]
                except KeyError:
                    t = self.get_attr_dtype(t[0])
            else:
                t = getattr(t, attr, None)
        return t


class Yield(pytypes.NamedTuple):
    expr: Expr

    @property
    def cycle_cond(self):
        return IntfReadyExpr()

    @property
    def exit_cond(self):
        return self.cycle_cond


# Blocks


@dataclass
class Block:
    stmts: list

    @property
    def in_cond(self):
        pass

    @property
    def cycle_cond(self):
        pass

    @property
    def exit_cond(self):
        pass


@dataclass
class IntfBlock(Block):
    intf: pytypes.Any

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)

    @property
    def exit_cond(self):
        return find_exit_cond(self.stmts)


class IntfLoop(Block, pytypes.NamedTuple):
    intf: pytypes.Any
    stmts: list
    multicycle: list = None

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        return and_expr(self.intf, find_cycle_cond(self.stmts))

    @property
    def exit_cond(self):
        exit_condition = find_exit_cond(self.stmts)
        intf_expr = IntfExpr(self.intf.intf, context='eot')

        return and_expr(intf_expr, exit_condition)


class IfBlock(Block, pytypes.NamedTuple):
    in_cond: Expr
    stmts: list

    @property
    def cycle_cond(self):
        condition = find_cycle_cond(self.stmts)
        if condition is None:
            return None

        return BinOpExpr((UnaryOpExpr(self.in_cond, '!'),
                          and_expr(self.in_cond, condition)),
                         operator='||')

    @property
    def exit_cond(self):
        condition = find_exit_cond(self.stmts)
        if condition is None:
            return None

        return BinOpExpr((UnaryOpExpr(self.in_cond, '!'),
                          and_expr(self.in_cond, condition)),
                         operator='||')


class IfElseBlock(Block, pytypes.NamedTuple):
    in_cond: Expr
    if_block: Block
    else_block: Block

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)

    @property
    def exit_cond(self):
        return find_exit_cond(self.stmts)


class Loop(Block, pytypes.NamedTuple):
    in_cond: Expr
    stmts: list
    exit_c: Expr
    multicycle: list = None

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)

    @property
    def exit_cond(self):
        return and_expr(self.cycle_cond,
                        and_expr(self.exit_c, find_exit_cond(self.stmts)))


@dataclass
class Module:
    in_ports: pytypes.List
    out_ports: pytypes.List
    locals: pytypes.Dict
    regs: pytypes.Dict
    variables: pytypes.Dict
    stmts: pytypes.List

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)

    @property
    def exit_cond(self):
        return find_exit_cond(self.stmts)


def isloop(block):
    return isinstance(block, Loop) or isinstance(block, IntfLoop)
