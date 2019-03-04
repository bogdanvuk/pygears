import inspect
import re
import typing as pytypes
from dataclasses import dataclass, field
from functools import reduce
from string import Template

from pygears.typing import Bool, Integer, Queue, Tuple, Uint, is_type, typeof

BOOLEAN_OPERATORS = {'|', '&', '^', '~', '!', '&&', '||'}
BIN_OPERATORS = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
EXTENDABLE_OPERATORS = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]

COND_NAME = Template('${cond_type}_cond_block_${block_id}')


def find_sub_cond_ids(cond):
    # TODO need to be replaced with expr visitor for operands
    res = {}
    if cond:
        pattern = re.compile('(.*)_cond_block_(.*)')
        for match in re.finditer('\w+_cond_block_\d+', str(cond)):
            sub_cond = match.group(0)
            cond_name, cond_id = pattern.search(sub_cond).groups()
            if cond_name in res:
                res[cond_name].append(int(cond_id))
            else:
                res[cond_name] = [int(cond_id)]

        return res

    return None


def find_cond_id(cond):
    if cond:
        return int(cond.split('_')[-1])

    return None


def nested_cond(stmt, cond_type):
    cond = getattr(stmt, f'{cond_type}_cond', None)

    if cond is None:
        return None

    if isinstance(cond, str):
        return cond

    return COND_NAME.substitute(cond_type=cond_type, block_id=stmt.id)


def nested_cycle_cond(stmt):
    return nested_cond(stmt, 'cycle')


def nested_exit_cond(stmt):
    return nested_cond(stmt, 'exit')


def create_oposite(expr):
    if isinstance(expr, UnaryOpExpr) and expr.operator == '!':
        return expr.operand

    return UnaryOpExpr(expr, '!')


def find_exit_cond(statements, search_in_cond=False):
    def has_in_cond(stmt):
        if search_in_cond and (not isinstance(stmt, IfBlock)) and hasattr(
                stmt, 'in_cond') and (stmt.in_cond is not None):
            return True
        return False

    for stmt in reversed(statements):
        cond = getattr(stmt, 'exit_cond', None)
        if cond is not None:
            exit_c = nested_exit_cond(stmt)
            if has_in_cond(stmt):
                return and_expr(exit_c, stmt.in_cond)

            return exit_c

        if has_in_cond(stmt):
            return stmt.in_cond

    return None


def find_cycle_cond(statements):
    cond = []
    for stmt in statements:
        cycle_c = getattr(stmt, 'cycle_cond', None)
        if cycle_c is not None:
            cond.append(nested_cycle_cond(stmt))

    return reduce(and_expr, cond, None)


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
    def name(self):
        if isinstance(self.out_port, str):
            return self.out_port

        return self.out_port.name

    @property
    def dtype(self):
        return Bool

    def __hash__(self):
        return hash(self.name)


@dataclass
class IntfValidExpr(Expr):
    port: pytypes.Any

    @property
    def name(self):
        if isinstance(self.port, str):
            return self.port

        return self.port.name

    @property
    def dtype(self):
        return Bool

    def __hash__(self):
        return hash(self.name)


@dataclass
class ResExpr(Expr):
    val: pytypes.Any

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)

        if isinstance(self.val, (list, tuple)):
            res = []
            for val in self.val:
                if is_type(type(val)):
                    res.append(type(val))
                else:
                    if val is not None:
                        res.append(Integer(val))
                    else:
                        res.append(None)
            return res

        if self.val is not None:
            return Integer(self.val)

        return None


@dataclass
class RegDef(Expr):
    val: pytypes.Any
    name: str

    @property
    def dtype(self):
        if is_type(type(self.val)):
            return type(self.val)

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
        return Uint[1] if (self.operand == '!') else self.operand.dtype


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

        if not isinstance(self.index, slice):
            return self.val.dtype[self.index]

        return self.val.dtype.__getitem__(self.index)


@dataclass
class AttrExpr(Expr):
    val: Expr
    attr: list

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
    operands: tuple
    cond: Expr

    @property
    def dtype(self):
        return max([op.dtype for op in self.operands])


@dataclass
class AssertExpr(Expr):
    test: Expr
    msg: str


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

        return or_expr(UnaryOpExpr(self.in_cond, '!'), condition)

    @property
    def exit_cond(self):
        condition = find_exit_cond(self.stmts)
        if condition is None:
            return None

        return or_expr(UnaryOpExpr(self.in_cond, '!'), condition)


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
    ports: pytypes.Any

    @property
    def expr(self):
        assert len(self.stmts) == 1, 'Yield block can only have 1 stmt'
        return self.stmts[0]

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


class TypeVisitor:
    def visit(self, node, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        if kwds:
            sig = inspect.signature(visitor)

        if kwds and ('kwds' in sig.parameters):
            return visitor(node, **kwds)

        return visitor(node)

    def generic_visit(self, node):
        raise Exception


class Conditions:
    def __init__(self):
        self.scope = []
        self.cycle_conds = []
        self.exit_conds = []

    @property
    def cycle_cond(self):
        cond = []
        for c_block in reversed(self.scope[1:]):
            # state changes break the cycle
            if len(c_block.state_ids) > len(self.scope[-1].state_ids):
                break

            block = c_block.hdl_block
            if isinstance(block, ContainerBlock):
                continue

            if block.cycle_cond and block.cycle_cond != 1:
                cond.append(nested_cycle_cond(block))
                self.cycle_conds.append(find_cond_id(cond[-1]))

            if hasattr(block, 'multicycle') and block.multicycle:
                break

        cond = set(cond)
        return reduce(and_expr, cond, None)

    @property
    def exit_cond(self):
        block = self.scope[-1].hdl_block
        cond = nested_exit_cond(block)
        if cond is not None:
            self.exit_conds.append(find_cond_id(cond))
        return cond

    @property
    def rst_cond(self):
        if len(self.scope) == 1:
            assert isinstance(self.scope[0].hdl_block, Module)
            block = self.scope[0].hdl_block.stmts
        else:
            block = [s.hdl_block for s in self.scope[1:]]
        return find_exit_cond(block, search_in_cond=True)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()
