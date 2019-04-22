import typing
from dataclasses import dataclass, field

from .hls_expressions import (Expr, IntfDef, IntfReadyExpr, OpType,
                              UnaryOpExpr, binary_expr)

# Conditions


def subcond_expr(cond, other=None):
    if other is None:
        return None

    if cond.expr is not None:
        return binary_expr(cond.expr, other, cond.operator)

    return other


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
class BaseLoop(Block):
    multicycle: typing.List[Expr]

    @property
    def cycle_cond(self):
        return CycleSubCond()


@dataclass
class IntfBlock(Block):
    intf: IntfDef

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
    intf: IntfDef

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
    stmts: typing.List[Block]

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
    _in_cond: typing.Union[Expr, None]
    _exit_cond: typing.Union[Expr, None]

    @property
    def exit_cond(self):
        return BothSubCond(self._exit_cond, '&&')


@dataclass
class Yield(Block):
    ports: typing.List[IntfDef]

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
class Module(Block):
    id: int = field(init=False, default=0)

    @property
    def cycle_cond(self):
        return CycleSubCond()

    @property
    def exit_cond(self):
        return ExitSubCond()
