import re
from functools import partial, reduce
from string import Template

from .hls_blocks import IfBlock
from .hls_expressions import and_expr, binary_expr

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


def find_sub_cond_ids(cond):
    # TODO need to be replaced with expr visitor for operands
    res = {}
    if cond:
        pattern = re.compile('(.*)_cond_block_(.*)')
        for match in re.finditer('\w+_cond_block_\d+', str(cond)):
            sub_cond = match.group(0)
            cond_name, cond_id = pattern.search(sub_cond).groups()
            if cond_name in res:
                res[cond_name].append(int(cond_id))
            else:
                res[cond_name] = [int(cond_id)]

        return res

    return None


def find_cond_id(cond):
    if cond:
        return int(cond.split('_')[-1])

    return None


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
                return and_expr(exit_c, in_c)

            return exit_c

        if has_in_cond(stmt):
            return nested_in_cond(stmt)

    return None


class ConditionsBase:
    # shared across all visitors
    in_conds = []
    cycle_conds = []
    exit_conds = []
    combined_conds = {}

    def init(self):
        self.in_conds.clear()
        self.cycle_conds.clear()
        self.exit_conds.clear()
        self.combined_conds.clear()

    def add_cond(self, cond, cond_type):
        assert cond is not None, f'Attempting to add None id to {cond_type} conditions'
        conds = getattr(self, f'{cond_type}_conds')
        if cond not in conds:
            conds.append(cond)

    def add_in_cond(self, cond):
        self.add_cond(cond, 'in')

    def add_cycle_cond(self, cond):
        self.add_cond(cond, 'cycle')

    def add_exit_cond(self, cond):
        self.add_cond(cond, 'exit')

    def combine_conditions(self, conds, operator='&&'):
        if not conds:
            return None

        if len(conds) == 1:
            return conds[0]

        name = COMBINED_COND_NAME.substitute(cond_id=len(self.combined_conds))
        self.combined_conds[name] = reduce(
            partial(binary_expr, operator=operator), conds, None)
        return name
