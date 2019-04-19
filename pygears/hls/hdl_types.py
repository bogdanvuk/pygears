import ast
import inspect
import typing as pytypes
from dataclasses import dataclass, field

from pygears.core.port import InPort, OutPort
from pygears.typing import Bool, Integer, Queue, Tuple, Uint, is_type, typeof

BOOLEAN_OPERATORS = {'|', '&', '^', '~', '!', '&&', '||'}
BIN_OPERATORS = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
EXTENDABLE_OPERATORS = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]

OPMAP = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
    ast.Pow: '**',
    ast.LShift: '<<',
    ast.RShift: '>>>',
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
    ast.Or: '||',
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


def subcond_expr(cond, other=None):
    if other is None:
        return None

    if cond.expr is not None:
        return binary_expr(cond.expr, other, cond.operator)

    return other


def find_name(node):
    name = getattr(node, 'name', None)
    if name is not None:
        return name

    if hasattr(node, 'val'):
        return find_name(node.val)

    if hasattr(node, 'op'):
        return find_name(node.op)

    return None


def find_sub_dtype(val):
    if isinstance(val, (tuple, list)):
        sub = max(val, key=lambda x: int(getattr(x, 'dtype')))
        return sub.dtype

    return val.dtype


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

    @property
    def name(self):
        return find_name(self.reg)


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

    @property
    def name(self):
        return find_name(self.variable)


@dataclass
class OperandVal(Expr):
    op: pytypes.Union[VariableDef, RegDef]
    context: str

    @property
    def dtype(self):
        return find_sub_dtype(self.op)


@dataclass
class IntfDef(Expr):
    intf: pytypes.Union[InPort, OutPort]
    _name: str = None
    context: str = None

    @property
    def name(self):
        if self._name:
            return self._name
        return self.intf.basename

    @property
    def dtype(self):
        return find_sub_dtype(self.intf)


@dataclass
class IntfStmt(Expr):
    intf: IntfDef
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

    def __hash__(self):
        return hash(find_name(self.val))


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
    break_cond: list = field(init=False, default=None)

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
class BaseLoop(Block):
    multicycle: list

    @property
    def cycle_cond(self):
        return CycleSubCond()


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
class IntfLoop(BaseLoop):
    intf: pytypes.Any

    @property
    def in_cond(self):
        return self.intf

    @property
    def exit_cond(self):
        intf_expr = IntfDef(
            intf=self.intf.intf, _name=self.intf.name, context='eot')

        return ExitSubCond(intf_expr, '&&')


@dataclass
class IfBlock(Block):
    _in_cond: Expr

    @property
    def in_cond(self):
        return self._in_cond

    @property
    def cycle_cond(self):
        if self.in_cond is not None:
            from .conditions_utils import COND_NAME
            in_c = COND_NAME.substitute(cond_type='in', block_id=self.id)
            return CycleSubCond(UnaryOpExpr(in_c, '!'), '||')
        return CycleSubCond()

    @property
    def exit_cond(self):
        if self.in_cond is not None:
            from .conditions_utils import COND_NAME
            in_c = COND_NAME.substitute(cond_type='in', block_id=self.id)
            return ExitSubCond(UnaryOpExpr(in_c, '!'), '||')
        return ExitSubCond()


@dataclass
class ContainerBlock(Block):
    stmts: pytypes.List[Block]

    @property
    def cycle_cond(self):
        from .conditions_utils import COND_NAME
        return COND_NAME.substitute(cond_type='cycle', block_id=self.id)

    @property
    def exit_cond(self):
        from .conditions_utils import COND_NAME
        return COND_NAME.substitute(cond_type='exit', block_id=self.id)


@dataclass
class Loop(BaseLoop):
    _in_cond: Expr
    _exit_cond: Expr

    @property
    def exit_cond(self):
        return BothSubCond(self._exit_cond, '&&')


@dataclass
class Yield(Block):
    ports: pytypes.Any

    @property
    def expr(self):
        if len(self.stmts) == 1:
            return self.stmts[0]
        return self.stmts

    @property
    def cycle_cond(self):
        return IntfReadyExpr(self.ports)

    @property
    def exit_cond(self):
        return self.cycle_cond


@dataclass
class ModuleData:
    in_ports: pytypes.Dict
    out_ports: pytypes.Dict
    hdl_locals: pytypes.Dict
    regs: pytypes.Dict
    variables: pytypes.Dict
    in_intfs: pytypes.Dict
    out_intfs: pytypes.Dict
    local_namespace: pytypes.Dict

    def get_container(self, name):
        for attr in ['regs', 'variables', 'in_intfs', 'out_intfs']:
            data_inst = getattr(self, attr)
            if name in data_inst:
                return data_inst
        # hdl_locals is last because it contain others
        if name in self.hdl_locals:
            return self.hdl_locals
        return None

    def get(self, name):
        data_container = self.get_container(name)
        if data_container is not None:
            return data_container[name]
        return None


@dataclass
class Module(Block):
    id: int = field(init=False, default=0)

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
