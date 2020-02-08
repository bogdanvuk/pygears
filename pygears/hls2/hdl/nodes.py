from dataclasses import dataclass, field
from typing import Any, Dict, List, Union
import textwrap

from pygears.typing.base import TypingMeta
from pygears.typing import Bool

from ..pydl import nodes as pydl


@dataclass
class AssignValue:
    target: Union[str, pydl.IntfOpExpr]
    val: Union[str, int, pydl.Expr]
    dtype: Union[TypingMeta, None] = None
    in_cond: pydl.Expr = pydl.ResExpr(True)
    opt_in_cond: pydl.Expr = pydl.ResExpr(True)
    exit_cond: pydl.Expr = pydl.ResExpr(True)

    def __str__(self):

        footer = ''
        if self.exit_cond != pydl.ResExpr(True):
            footer = f' (exit: {str(self.exit_cond)})'

        return f'{str(self.target)} <= {str(self.val)}{footer}\n'


@dataclass
class AssertValue:
    val: Any


@dataclass
class BaseBlock:
    # TODO : newer versions of Python will not need the string
    stmts: List[Union[AssignValue, 'HDLBlock']]
    dflts: Dict[Union[str, pydl.IntfOpExpr], AssignValue]

    @property
    def dflt_stmts(self):
        return list(self.dflts.values())


@dataclass
class HDLBlock(BaseBlock):
    in_cond: pydl.Expr = pydl.ResExpr(True)
    opt_in_cond: pydl.Expr = pydl.ResExpr(True)
    exit_cond: pydl.Expr = pydl.ResExpr(True)

    def __str__(self):
        body = ''
        conds = {
            'in': self.in_cond,
            'opt_in': self.opt_in_cond,
        }
        header = []
        for name, val in conds.items():
            if val != pydl.ResExpr(True):
                header.append(f'{name}: {str(val)}')

        if header:
            header = '(' + ', '.join(header) + ') '
        else:
            header = ''

        footer = ''
        if self.exit_cond != pydl.ResExpr(True):
            footer = f' (exit: {str(self.exit_cond)})'

        for s in self.stmts:
            body += str(s)

        if not header and body.count('\n') == 1:
            return f'{body[:-1]}{footer}\n'

        return f'{header}{{\n{textwrap.indent(body, "    ")}}}{footer}\n'


@dataclass
class IfElseBlock(HDLBlock):
    def __str__(self):
        return f'IfElse {super().__str__()}'


@dataclass
class StateBlock(BaseBlock):
    pass


@dataclass
class CombBlock(HDLBlock):
    funcs: List = field(default_factory=list)


@dataclass
class FuncBlock(BaseBlock):
    args: List[pydl.VariableDef]
    name: str
    ret_dtype: pydl.PgType
    in_cond: pydl.Expr = pydl.ResExpr(True)
    opt_in_cond: pydl.Expr = pydl.ResExpr(True)
    funcs: List = field(default_factory=list)

    def __str__(self):
        body = ''
        for s in self.stmts:
            body += str(s)

        args = [f'{name}: {val}' for name, val in self.args.items()]
        return f'{self.name}({", ".join(args)}) {{\n{textwrap.indent(body, "    ")}}}\n'


@dataclass
class FuncReturn:
    func: FuncBlock
    expr: pydl.Expr

    def __str__(self):
        return f'return {self.expr}'


@dataclass
class CombSeparateStmts:
    stmts: List[AssignValue]
