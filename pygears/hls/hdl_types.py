from dataclasses import dataclass
from typing import Any, Dict, List, Union

from pygears.typing.base import TypingMeta

from .hls_expressions import Expr, VariableDef, PgType, IntfOpExpr


@dataclass
class AssignValue:
    target: Union[str, IntfOpExpr]
    val: Union[str, int, Expr]
    dtype: Union[TypingMeta, None] = None


@dataclass
class AssertValue:
    val: Any


@dataclass
class BaseBlock:
    # TODO : newer versions of Python will not need the string
    stmts: List[Union[AssignValue, 'HDLBlock']]
    dflts: Dict[Union[str, IntfOpExpr], AssignValue]

    @property
    def dflt_stmts(self):
        return list(self.dflts.values())


@dataclass
class HDLBlock(BaseBlock):
    in_cond: str = None


@dataclass
class CombBlock(BaseBlock):
    pass


@dataclass
class FuncBlock(BaseBlock):
    args: List[VariableDef]
    name: str
    ret_dtype: PgType


@dataclass
class FuncReturn:
    func: FuncBlock
    expr: Expr


@dataclass
class CombSeparateStmts:
    stmts: List[AssignValue]
