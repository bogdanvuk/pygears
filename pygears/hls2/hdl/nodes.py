from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

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
    cycle_cond: pydl.Expr = pydl.ResExpr(True)


@dataclass
class IfElseBlock(HDLBlock):
    pass


@dataclass
class StateBlock(BaseBlock):
    pass


@dataclass
class CombBlock(BaseBlock):
    in_cond: pydl.Expr = pydl.ResExpr(True)
    opt_in_cond: pydl.Expr = pydl.ResExpr(True)
    funcs: List = field(default_factory=list)


@dataclass
class FuncBlock(BaseBlock):
    args: List[pydl.VariableDef]
    name: str
    ret_dtype: pydl.PgType
    in_cond: pydl.Expr = pydl.ResExpr(True)
    opt_in_cond: pydl.Expr = pydl.ResExpr(True)
    funcs: List = field(default_factory=list)


@dataclass
class FuncReturn:
    func: FuncBlock
    expr: pydl.Expr


@dataclass
class CombSeparateStmts:
    stmts: List[AssignValue]
