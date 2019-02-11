import inspect
import re
import typing as pytypes
from dataclasses import dataclass, field
from functools import reduce
from string import Template

from pygears.typing import Bool, Integer, Queue, Tuple, Uint, is_type, typeof

bin_operators = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
extendable_operators = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]

cond_name = Template('${cond_type}_cond_block_${block_id}')


def find_sub_cond_ids(cond):
    # TODO need to be replaced with expr visitor for operands
    res = {}
    if cond:
        pattern = re.compile('(.*)_cond_block_(.*)')
        for m in re.finditer('\w+_cond_block_\d+', str(cond)):
            sub_cond = m.group(0)
            cond_name, cond_id = pattern.search(sub_cond).groups()
            if cond_name in res:
                res[cond_name].append(int(cond_id))
            else:
                res[cond_name] = [int(cond_id)]

        return res


def find_cond_id(cond):
    if cond:
        return int(cond.split('_')[-1])


def nested_cond(stmt, cond_type):
    cond = getattr(stmt, f'{cond_type}_cond', None)
    if cond is not None:
        if isinstance(cond, str):
            return cond
        else:
            return cond_name.substitute(cond_type=cond_type, block_id=stmt.id)


def nested_cycle_cond(stmt):
    return nested_cond(stmt, 'cycle')


def nested_exit_cond(stmt):
    return nested_cond(stmt, 'exit')


def create_oposite(expr):
    if isinstance(expr, UnaryOpExpr) and expr.operator == '!':
        return expr.operand
    else:
        return UnaryOpExpr(expr, '!')


def find_exit_cond(statements, search_in_cond=False):
    for stmt in reversed(statements):
        c = getattr(stmt, 'exit_cond', None)
        if c is not None:
            exit_c = nested_exit_cond(stmt)
            if search_in_cond and (not isinstance(stmt, IfBlock)) and hasattr(
                    stmt, 'in_cond') and (stmt.in_cond is not None):
                return and_expr(exit_c, stmt.in_cond)
            else:
                return exit_c

    return None


def find_cycle_cond(statements):
    cond = []
    for stmt in statements:
        c = getattr(stmt, 'cycle_cond', None)
        if c is not None:
            cond.append(nested_cycle_cond(stmt))

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


@dataclass
class Expr:
    @property
    def dtype(self):
        pass


@dataclass
class IntfReadyExpr(Expr):
    out_port: pytypes.Any

    @property
    def dtype(self):
        return Bool


@dataclass
class ResExpr(Expr):
    val: pytypes.Any

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)
        else:
            if isinstance(self.val, (list, tuple)):
                res = []
                for v in self.val:
                    if is_type(type(v)):
                        res.append(type(v))
                    else:
                        if v is not None:
                            res.append(Integer(v))
                        else:
                            res.append(None)
                return res
            else:
                if self.val is not None:
                    return Integer(self.val)


@dataclass
class RegDef(Expr):
    val: pytypes.Any
    name: str

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)
        else:
            return self.val.dtype


@dataclass
class RegNextStmt(Expr):
    reg: RegDef
    val: Expr

    @property
    def dtype(self):
        return self.reg.dtype


@dataclass
class VariableDef(Expr):
    val: pytypes.Any
    name: str

    @property
    def dtype(self):
        return self.val.dtype


@dataclass
class VariableStmt(Expr):
    variable: VariableDef
    val: Expr

    @property
    def dtype(self):
        return self.variable.dtype


@dataclass
class OperandVal(Expr):
    op: pytypes.Union[VariableDef, RegDef]
    context: str

    @property
    def dtype(self):
        return self.op.dtype


@dataclass
class IntfExpr(Expr):
    intf: pytypes.Any
    context: str = None

    @property
    def name(self):
        return self.intf.basename

    @property
    def dtype(self):
        return self.intf.dtype


@dataclass
class IntfDef(Expr):
    intf: pytypes.Any
    name: str
    context: str = None

    @property
    def dtype(self):
        if isinstance(self.intf, tuple):
            return self.intf[0].dtype
        else:
            return self.intf.dtype


@dataclass
class IntfStmt(Expr):
    intf: IntfExpr
    val: Expr

    @property
    def dtype(self):
        return self.intf.dtype


@dataclass
class ConcatExpr(Expr):
    operands: tuple

    @property
    def dtype(self):
        return Tuple[tuple(op.dtype for op in self.operands)]


@dataclass
class UnaryOpExpr(Expr):
    operand: Expr
    operator: str

    @property
    def dtype(self):
        return Uint[1] if (self.operand is '!') else self.operand.dtype


@dataclass
class CastExpr(Expr):
    operand: Expr
    cast_to: pytypes.Any

    @property
    def dtype(self):
        return self.cast_to


@dataclass
class BinOpExpr(Expr):
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


@dataclass
class ArrayOpExpr(Expr):
    array: Expr
    operator: str

    @property
    def dtype(self):
        return Uint[1]


@dataclass
class SubscriptExpr(Expr):
    val: Expr
    index: pytypes.Any

    @property
    def dtype(self):
        if isinstance(self.index, OperandVal):
            return self.val.dtype[0]
        elif not isinstance(self.index, slice):
            return self.val.dtype[self.index]
        else:
            return self.val.dtype.__getitem__(self.index)


@dataclass
class AttrExpr(Expr):
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


@dataclass
class ConditionalExpr(Expr):
    operands: tuple
    cond: Expr

    @property
    def dtype(self):
        return max([op.dtype for op in self.operands])


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
        if isinstance(self.intf, IntfExpr):
            intf_expr = IntfExpr(self.intf.intf, context='eot')
        else:
            intf_expr = IntfDef(
                intf=self.intf.intf, name=self.intf.name, context='eot')
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
        if all([s.cycle_cond is None for s in self.stmts]):
            return None

        cond = None
        for block in self.stmts:
            block_cond = and_expr(block.cycle_cond, block.in_cond)
            cond = or_expr(cond, block_cond)
        return cond

    @property
    def exit_cond(self):
        # return and_expr(self.stmts[-1].exit_cond, self.stmts[-1].in_cond)
        if all([s.exit_cond is None for s in self.stmts]):
            return None

        cond = None
        for block in self.stmts:
            block_cond = and_expr(block.exit_cond, block.in_cond)
            cond = or_expr(cond, block_cond)
        return cond


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
class Yield(Block):
    expr: Expr
    ports: pytypes.Any

    @property
    def cycle_cond(self):
        return IntfReadyExpr(self.ports)

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
    intfs: pytypes.Dict
    out_intfs: pytypes.Dict
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


class TypeVisitor:
    def visit(self, node, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ is 'generic_visit' and isinstance(node, Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ is 'generic_visit' and isinstance(node, Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        if kwds:
            sig = inspect.signature(visitor)
        if kwds and ('kwds' in sig.parameters):
            return visitor(node, **kwds)
        else:
            return visitor(node)

    def generic_visit(self, node):
        breakpoint()
        raise Exception


class Conditions:
    def __init__(self):
        self.scope = []
        self.cycle_conds = []
        self.exit_conds = []

    @property
    def cycle_cond(self):
        cond = []
        for c in reversed(self.scope[1:]):
            s = c.hdl_block
            if isinstance(s, ContainerBlock):
                continue

            if s.cycle_cond and s.cycle_cond != 1:
                cond.append(nested_cycle_cond(s))
                self.cycle_conds.append(find_cond_id(cond[-1]))

            if hasattr(s, 'multicycle') and s.multicycle:
                break

        cond = set(cond)
        return reduce(and_expr, cond, None)

    @property
    def exit_cond(self):
        s = self.scope[-1].hdl_block
        c = nested_exit_cond(s)
        if c is not None:
            self.exit_conds.append(find_cond_id(c))
        return c

    @property
    def rst_cond(self):
        b = [s.hdl_block for s in self.scope[1:]]
        return find_exit_cond(b, search_in_cond=True)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()
