import re
from functools import partial, reduce
from string import Template

from . import hls_expressions as expr
from .hls_blocks import IfBlock, Module

COND_NAME = Template('${cond_type}_cond_block_${block_id}')
COMBINED_COND_NAME = Template('combined_cond_${cond_id}')


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


def nested_cond(stmt, cond_type):
    cond = getattr(stmt, f'{cond_type}_cond', None)

    if cond is None:
        return None

    if isinstance(cond, str):
        return cond

    return COND_NAME.substitute(cond_type=cond_type, block_id=stmt.id)


def nested_in_cond(stmt):
    return nested_cond(stmt, 'in')


def nested_cycle_cond(stmt):
    return nested_cond(stmt, 'cycle')


def nested_exit_cond(stmt):
    return nested_cond(stmt, 'exit')


def find_exit_cond(statements, search_in_cond=False):
    def has_in_cond(stmt):
        if search_in_cond and (not isinstance(stmt, IfBlock)) and hasattr(
                stmt, 'in_cond') and (stmt.in_cond is not None):
            return True
        return False

    for stmt in reversed(statements):
        cond = getattr(stmt, 'exit_cond', None)
        if cond is not None:
            exit_c = nested_exit_cond(stmt)
            if has_in_cond(stmt):
                in_c = nested_in_cond(stmt)
                return expr.and_expr(exit_c, in_c)

            return exit_c

        if has_in_cond(stmt):
            return nested_in_cond(stmt)

    return None


def find_rst_cond(module):
    assert isinstance(module, Module)
    return find_exit_cond(module.stmts, search_in_cond=True)


class UsedConditions:
    # shared across all visitors
    in_conds = []
    cycle_conds = []
    exit_conds = []
    combined_conds = []
    values_of_combined = []


def init_conditions():
    UsedConditions.in_conds.clear()
    UsedConditions.cycle_conds.clear()
    UsedConditions.exit_conds.clear()
    UsedConditions.combined_conds.clear()
    UsedConditions.values_of_combined.clear()


def add_found_cond(cond, cond_type):
    assert cond is not None, f'Attempting to add None id to {cond_type} conditions'
    conds = getattr(UsedConditions, f'{cond_type}_conds')
    if cond not in conds:
        conds.append(cond)


def add_in_cond(cond):
    add_found_cond(cond, 'in')


def add_cycle_cond(cond):
    add_found_cond(cond, 'cycle')


def add_exit_cond(cond):
    add_found_cond(cond, 'exit')


def add_cond(cond):
    cond_id, cond_t = find_cond_id_and_type(cond)
    add_found_cond(cond_id, cond_t)


def find_cond_id_and_type(cond):
    if cond:
        res = cond.split('_')
        return int(res[-1]), res[0]

    return None, None


def add_cond_expr_operands(cond):
    if cond is None:
        return

    if isinstance(cond, str):
        if cond_name_match(cond):
            cond_id, cond_t = find_cond_id_and_type(cond)
            add_found_cond(cond_id, cond_t)
            if cond_t == 'combined':
                add_cond_expr_operands(
                    UsedConditions.values_of_combined[cond_id])

    elif isinstance(cond, (expr.ConcatExpr, expr.BinOpExpr)):
        for op in cond.operands:
            add_cond_expr_operands(op)

    elif isinstance(cond, (expr.UnaryOpExpr, expr.CastExpr)):
        add_cond_expr_operands(cond.operand)


def combine_conditions(conds, operator='&&'):
    if not conds:
        return None

    if len(conds) == 1:
        return conds[0]

    name = COMBINED_COND_NAME.substitute(
        cond_id=len(UsedConditions.values_of_combined))
    UsedConditions.values_of_combined.append(
        reduce(partial(expr.binary_expr, operator=operator), conds, None))
    return name
