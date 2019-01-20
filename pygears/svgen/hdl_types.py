import typing as pytypes
from dataclasses import dataclass, field
from functools import reduce

from pygears.typing import Bool, Queue, Tuple, Uint, is_type, typeof

bin_operators = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
extendable_operators = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]


def find_exit_cond(statements, search_in_cond=False):
    for stmt in reversed(statements):
        if hasattr(stmt, 'exit_cond'):
            stmt_cond = stmt.exit_cond
            if stmt_cond is not None:
                if search_in_cond and hasattr(
                        stmt, 'in_cond') and (stmt.in_cond is not None):
                    return and_expr(stmt_cond, stmt.in_cond)
                else:
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


def binary_expr(expr1, expr2, operator):
    if expr1 is None:
        return expr2
    elif expr2 is None:
        return expr1
    elif expr1 is None and expr2 is None:
        return None
    else:
        return BinOpExpr((expr1, expr2), operator)


def and_expr(expr1, expr2):
    return binary_expr(expr1, expr2, '&&')


def or_expr(expr1, expr2):
    return binary_expr(expr1, expr2, '||')


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


class YieldStmt(pytypes.NamedTuple):
    expr: Expr


# Blocks


@dataclass
class Block:
    stmts: list
    id: int = field(init=False, default=None)

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


@dataclass
class IntfLoop(Block):
    intf: pytypes.Any
    multicycle: list = None

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)
        # return and_expr(self.intf, find_cycle_cond(self.stmts))

    @property
    def exit_cond(self):
        exit_condition = find_exit_cond(self.stmts)
        intf_expr = IntfExpr(self.intf.intf, context='eot')
        return and_expr(intf_expr, exit_condition)


@dataclass
class IfBlock(Block):
    _in_cond: Expr

    @property
    def in_cond(self):
        return self._in_cond

    @property
    def cycle_cond(self):
        condition = find_cycle_cond(self.stmts)
        if condition is None:
            return None

        return or_expr(
            UnaryOpExpr(self.in_cond, '!'), and_expr(self.in_cond, condition))

    @property
    def exit_cond(self):
        condition = find_exit_cond(self.stmts)
        if condition is None:
            return None

        return or_expr(
            UnaryOpExpr(self.in_cond, '!'), and_expr(self.in_cond, condition))


@dataclass
class ContainerBlock(Block):
    stmts: pytypes.List[Block]

    @property
    def cycle_cond(self):
        cond = None
        for block in self.stmts:
            block_cond = and_expr(block.cycle_cond, block.in_cond)
            cond = or_expr(cond, block_cond)
        return cond

    @property
    def exit_cond(self):
        return and_expr(self.stmts[-1].exit_cond, self.stmts[-1].in_cond)


@dataclass
class Loop(Block):
    _in_cond: Expr
    _exit_cond: Expr
    multicycle: list = None

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)

    @property
    def exit_cond(self):
        return and_expr(self.cycle_cond,
                        and_expr(self._exit_cond, find_exit_cond(self.stmts)))


@dataclass
class YieldBlock(Block):
    @property
    def cycle_cond(self):
        return IntfReadyExpr()

    @property
    def exit_cond(self):
        return self.cycle_cond


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

    @property
    def rst_cond(self):
        return find_exit_cond(self.stmts, search_in_cond=True)


def isloop(block):
    return isinstance(block, Loop) or isinstance(block, IntfLoop)
