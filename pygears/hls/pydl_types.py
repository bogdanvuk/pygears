import typing
from dataclasses import dataclass, field

from .hls_expressions import Expr, IntfDef, IntfReadyExpr, OpType, UnaryOpExpr

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
        intf_expr = IntfDef(intf=self.intf.intf,
                            _name=self.intf.name,
                            context='eot')

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
            from .conditions_utils import InCond, CondExpr
            in_c = InCond(self.id)
            return CycleSubCond(CondExpr(sub_expr=UnaryOpExpr(in_c, '!')),
                                '||')
        return CycleSubCond()

    @property
    def exit_cond(self):
        if self.in_cond is not None:
            from .conditions_utils import InCond, CondExpr
            in_c = InCond(self.id)
            return ExitSubCond(CondExpr(sub_expr=UnaryOpExpr(in_c, '!')), '||')
        return ExitSubCond()


@dataclass
class ContainerBlock(Block):
    stmts: typing.List[Block]

    @property
    def cycle_cond(self):
        from .conditions_utils import CycleCond
        return CycleCond(self.id)

    @property
    def exit_cond(self):
        from .conditions_utils import ExitCond
        return ExitCond(self.id)


@dataclass
class CombBlock(ContainerBlock):
    pass


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
            return self.write_line(f'{self.field_hdr}"{node.op.intf.basename}"')

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
            self.write_line(
                f'{self.field_hdr}(')
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
