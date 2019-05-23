import re
from dataclasses import dataclass
from string import Template
from typing import List

from . import hls_expressions as expr

COND_NAME = Template('${cond_type}_cond_block_${block_id}')
COMBINED_COND_NAME = Template('combined_cond_${cond_id}')

COND_TYPES = ['in', 'cycle', 'exit']


@dataclass
class CondBase:
    id: int = None


@dataclass
class CycleCond(CondBase):
    ctype = 'cycle'


@dataclass
class ExitCond(CondBase):
    ctype = 'exit'


@dataclass
class InCond(CondBase):
    ctype = 'in'


@dataclass
class CondExpr(CondBase):
    ctype = 'expr'
    sub_expr: expr.Expr = None


@dataclass
class CombinedCond(CondBase):
    ctype = 'combined'
    id: List[CondBase] = None
    operator: str = '&&'


@dataclass
class StateCond(CondBase):
    ctype = 'state'
    id: List[CondBase] = None
    state_ids: List[int] = None

    def state_expr(self, prev_cond):
        from .utils import state_expr
        assert len(self.id) == 1 or not self.id
        assert len(prev_cond) == 1 or not prev_cond
        prev = prev_cond[0] if prev_cond else None
        return state_expr(self.state_ids, prev)


def cond_name_match_by_type(name, cond_type):
    if not isinstance(name, str):
        return None

    pattern = re.compile(f'^{cond_type}_cond_block_\d+$')
    res = pattern.match(name)
    return res


def cond_name_match(name):
    if not isinstance(name, str):
        return None

    pattern = re.compile(f'^\w+_cond_block_\d+$')
    res = pattern.match(name)
    if res is not None:
        return res

    pattern = re.compile(f'^combined_cond_\d+$')
    return pattern.match(name)


class UsedConditions:
    # shared across all visitors
    in_conds = []
    cycle_conds = []
    exit_conds = []


def init_conditions():
    UsedConditions.in_conds.clear()
    UsedConditions.cycle_conds.clear()
    UsedConditions.exit_conds.clear()


def add_found_cond(cond, cond_type):
    assert cond is not None, f'Attempting to add None id to {cond_type} conditions'
    conds = getattr(UsedConditions, f'{cond_type}_conds')
    if cond not in conds:
        conds.append(cond)


def add_cond(cond):
    cond_id, cond_t = find_cond_id_and_type(cond)
    add_found_cond(cond_id, cond_t)


def find_cond_id_and_type(cond):
    if cond:
        res = cond.split('_')
        return int(res[-1]), res[0]

    return None, None


def combine(conds, operator='&&'):
    if not conds:
        return None

    if len(conds) == 1:
        return conds[0]

    unique_conds = []

    def append_unique(c):
        if c not in unique_conds:
            unique_conds.append(c)

    for c in conds:
        if isinstance(c, CombinedCond) and c.operator == operator:
            for comb_c in c.id:
                append_unique(comb_c)
        else:
            append_unique(c)
    return CombinedCond(id=unique_conds, operator=operator)
