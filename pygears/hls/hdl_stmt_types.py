from dataclasses import dataclass
from typing import Any, Dict, List, Union

from pygears.typing.base import TypingMeta

from .hdl_types import Expr


@dataclass
class AssignValue:
    target: Union[str, Expr]
    val: Union[str, int, Expr]
    dtype: Union[TypingMeta, None] = None


@dataclass
class AssertValue:
    val: Any


@dataclass
class BaseBlock:
    # TODO : newer versions of Python will not need the string
    stmts: List[Union[AssignValue, 'HDLBlock']]
    dflts: Dict  # values are AssignValue, keys target of AssignValue

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
class CombSeparateStmts:
    stmts: List[AssignValue]
