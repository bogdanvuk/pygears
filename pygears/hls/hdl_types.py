import inspect
import typing as pytypes
from dataclasses import dataclass, field

from pygears.typing import Bool, Integer, Queue, Tuple, Uint, is_type, typeof

BOOLEAN_OPERATORS = {'|', '&', '^', '~', '!', '&&', '||'}
BIN_OPERATORS = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
EXTENDABLE_OPERATORS = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]


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


def subcond_expr(cond, other=None):
    if other is None:
        return None

    if cond.expr is not None:
        return binary_expr(cond.expr, other, cond.operator)

    return other


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


# Conditions


@dataclass
class SubConditions:
    expr: Expr = None
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
        return CycleSubCond()

    @property
    def exit_cond(self):
        return ExitSubCond()


@dataclass
class IntfLoop(Block):
    intf: pytypes.Any
    multicycle: list = None

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        return CycleSubCond()

    @property
    def exit_cond(self):
        if isinstance(self.intf, IntfExpr):
            intf_expr = IntfExpr(self.intf.intf, context='eot')
        else:
            intf_expr = IntfDef(
                intf=self.intf.intf, name=self.intf.name, context='eot')

        return ExitSubCond(intf_expr, '&&')


@dataclass
class IfBlock(Block):
    _in_cond: Expr

    @property
    def in_cond(self):
        return self._in_cond

    @property
    def cycle_cond(self):
        return CycleSubCond(UnaryOpExpr(self.in_cond, '!'), '||')

    @property
    def exit_cond(self):
        return ExitSubCond(UnaryOpExpr(self.in_cond, '!'), '||')


@dataclass
class ContainerBlock(Block):
    stmts: pytypes.List[Block]

    @property
    def cycle_cond(self):
        from .conditions import COND_NAME
        return COND_NAME.substitute(cond_type='cycle', block_id=self.id)

    @property
    def exit_cond(self):
        from .conditions import COND_NAME
        return COND_NAME.substitute(cond_type='exit', block_id=self.id)


@dataclass
class Loop(Block):
    _in_cond: Expr
    _exit_cond: Expr
    multicycle: list = None

    @property
    def cycle_cond(self):
        return CycleSubCond()

    @property
    def exit_cond(self):
        return BothSubCond(self._exit_cond, '&&')


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
        return CycleSubCond()

    @property
    def exit_cond(self):
        return ExitSubCond()


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
