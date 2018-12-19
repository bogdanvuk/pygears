import typing as pytypes

from pygears.typing import Tuple, typeof, Uint, Queue, is_type, Bool

bin_operators = ['!', '==', '>', '>=', '<', '<=', '!=', '&&', '||']
extendable_operators = [
    '+', '-', '*', '/', '%', '**', '<<', '>>>', '|', '&', '^', '/', '~', '!'
]


def find_exit_cond(statements):
    cond = []
    for stmt in statements:
        if hasattr(stmt, 'exit_cond'):
            stmt_cond = stmt.exit_cond
            if stmt_cond is not None:
                cond.append(stmt_cond)
    return cond


def find_cycle_cond(statements):
    cond = []
    for stmt in statements:
        # if hasattr(stmt, 'cycle_cond') and not stmt.in_cond:
        if hasattr(stmt, 'cycle_cond'):
            stmt_cond = stmt.cycle_cond
            if stmt_cond is not None:
                cond.append(stmt_cond)

    return cond


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


# Blocks


class Block:
    @property
    def in_cond(self):
        pass

    @property
    def cycle_cond(self):
        pass

    @property
    def exit_cond(self):
        pass


class IntfBlock(Block, pytypes.NamedTuple):
    intf: pytypes.Any
    stmts: list

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)[0]

    @property
    def exit_cond(self):
        exit_conditions = find_exit_cond(self.stmts)
        if len(exit_conditions) == 0:
            return None
        elif len(exit_conditions) > 1:
            raise Exception
        else:
            return exit_conditions[0]


class IntfLoop(Block, pytypes.NamedTuple):
    intf: pytypes.Any
    stmts: list
    multicycle: list = None

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)[0]

    @property
    def exit_cond(self):
        exit_conditions = find_exit_cond(self.stmts)
        if len(exit_conditions) == 0:
            exit_c = None
        elif len(exit_conditions) > 1:
            raise Exception
        else:
            exit_c = exit_conditions[0]

        intf_expr = IntfExpr(self.intf.intf, context='eot')
        if exit_c is not None:
            return BinOpExpr((intf_expr, exit_c), '&&')
        else:
            return intf_expr


class IfBlock(Block, pytypes.NamedTuple):
    in_cond: Expr
    stmts: list

    @property
    def cycle_cond(self):
        conditions = find_cycle_cond(self.stmts)
        if len(conditions) == 0:
            return None
        elif len(conditions) > 1:
            raise Exception
        else:
            condition = conditions[0]

        return BinOpExpr((UnaryOpExpr(self.in_cond, '!'),
                          BinOpExpr((self.in_cond, condition), '&&')),
                         operator='||')


class IfElseBlock(Block, pytypes.NamedTuple):
    in_cond: Expr
    if_block: Block
    else_block: Block

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)


class Loop(Block, pytypes.NamedTuple):
    in_cond: Expr
    stmts: list
    exit_c: Expr
    multicycle: list = None

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)[0]

    @property
    def exit_cond(self):
        exit_conditions = find_exit_cond(self.stmts)
        if len(exit_conditions) == 0:
            exit_c = None
        elif len(exit_conditions) > 1:
            raise Exception
        else:
            exit_c = exit_conditions[0]

        if exit_c is not None:
            return BinOpExpr((self.exit_c, exit_c), '&&')
        else:
            return self.exit_c


class Stage(Block, pytypes.NamedTuple):
    state_var: RegVal
    state_id: int

    @property
    def in_cond(self):
        return BinOpExpr(
            (self.state_var, ResExpr(self.state_var.dtype(self.state_id))),
            '==')

    @property
    def cycle_cond(self):
        return find_cycle_cond(self.stmts)[0]

    @property
    def exit_cond(self):
        exit_conditions = find_exit_cond(self.stmts)
        if len(exit_conditions) == 0:
            exit_c = None
        elif len(exit_conditions) > 1:
            raise Exception
        else:
            exit_c = exit_conditions[0]

        if exit_c is not None:
            return BinOpExpr((self.in_cond, exit_c), '&&')
        else:
            return self.in_cond


class Module(pytypes.NamedTuple):
    in_ports: pytypes.List
    out_ports: pytypes.List
    locals: pytypes.Dict
    regs: pytypes.Dict
    stages: pytypes.List
    variables: pytypes.Dict
    stmts: pytypes.List


def isloop(block):
    return isinstance(block, Loop) or isinstance(block, IntfLoop)
