import typing as pytypes
from dataclasses import dataclass

from pygears.typing.base import TypingMeta


@dataclass
class AssignValue:
    target: pytypes.Any
    val: pytypes.Any
    width: TypingMeta = None


@dataclass
class CombBlock:
    stmts: pytypes.List
    dflts: pytypes.Dict


@dataclass
class CombSeparateStmts:
    stmts: pytypes.List


@dataclass
class HDLBlock:
    stmts: pytypes.List
    dflts: pytypes.Dict
    in_cond: str = None
