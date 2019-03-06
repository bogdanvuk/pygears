import re
from functools import reduce
from string import Template

from . import hdl_types as ht

COND_NAME = Template('${cond_type}_cond_block_${block_id}')
COMBINED_COND_NAME = Template('combined_cond_${cond_id}')


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


def nested_cond(stmt, cond_type):
    cond = getattr(stmt, f'{cond_type}_cond', None)

    if cond is None:
        return None

    if isinstance(cond, str):
        return cond

    return COND_NAME.substitute(cond_type=cond_type, block_id=stmt.id)


def nested_cycle_cond(stmt):
    return nested_cond(stmt, 'cycle')


def nested_exit_cond(stmt):
    return nested_cond(stmt, 'exit')


def find_exit_cond(statements, search_in_cond=False):
    def has_in_cond(stmt):
        if search_in_cond and (not isinstance(stmt, ht.IfBlock)) and hasattr(
                stmt, 'in_cond') and (stmt.in_cond is not None):
            return True
        return False

    for stmt in reversed(statements):
        cond = getattr(stmt, 'exit_cond', None)
        if cond is not None:
            exit_c = nested_exit_cond(stmt)
            if has_in_cond(stmt):
                return ht.and_expr(exit_c, stmt.in_cond)

            return exit_c

        if has_in_cond(stmt):
            return stmt.in_cond

    return None


class Conditions:
    # shared across all visitors
    cycle_conds = []
    exit_conds = []
    combined_cycle_conds = {}
    combined_exit_conds = {}

    def __init__(self):
        self.scope = []

    def add_cycle_cond(self, cond):
        if cond not in self.cycle_conds:
            self.cycle_conds.append(cond)

    def add_exit_cond(self, cond):
        if cond is None:
            return

        if cond not in self.exit_conds:
            self.exit_conds.append(cond)

    def block_cycle_cond(self, block):
        curr_cond = block.cycle_cond
        if not isinstance(curr_cond, ht.CycleSubCond):
            return curr_cond

        assert block == self.scope[-1].hdl_block

        conds = []
        for child in self.scope[-1].child:
            if child.hdl_block.cycle_cond is not None:
                conds.append(nested_cycle_cond(child.hdl_block))
        sub_conds = reduce(ht.and_expr, conds, None)

        if curr_cond.expr is not None:
            return ht.binary_expr(curr_cond.expr, sub_conds,
                                  curr_cond.operator)

        return sub_conds

    def block_exit_cond(self, block):
        curr_cond = block.exit_cond
        if not isinstance(curr_cond, ht.ExitSubCond):
            return curr_cond

        assert block == self.scope[-1].hdl_block

        exit_c = None
        for child in reversed(self.scope[-1].child):
            child_exit_cond = getattr(child.hdl_block, 'exit_cond', None)
            if child_exit_cond is not None:
                exit_c = nested_exit_cond(child.hdl_block)
                break

        if curr_cond.expr is not None:
            if exit_c is not None:
                return ht.binary_expr(curr_cond.expr, exit_c,
                                      curr_cond.operator)
            return curr_cond.expr

        return exit_c

    @property
    def cycle_cond(self):
        cond = []
        for c_block in reversed(self.scope[1:]):
            # state changes break the cycle
            if len(c_block.state_ids) > len(self.scope[-1].state_ids):
                break

            block = c_block.hdl_block
            if isinstance(block, ht.ContainerBlock):
                continue

            if block.cycle_cond and block.cycle_cond != 1:
                cond.append(nested_cycle_cond(block))
                self.add_cycle_cond(find_cond_id(cond[-1]))

            if hasattr(block, 'multicycle') and block.multicycle:
                break

        cond = list(set(cond))
        if len(cond) > 1:
            name = COMBINED_COND_NAME.substitute(
                cond_id=len(self.combined_cycle_conds))
            self.combined_cycle_conds[name] = reduce(ht.and_expr, cond, None)
            return name

        return cond[0]

    def _exit_cond(self, block):
        cond = nested_exit_cond(block)
        self.add_exit_cond(find_cond_id(cond))
        return cond

    @property
    def exit_cond(self):
        block = self.scope[-1].hdl_block
        return self._exit_cond(block)

    def get_exit_cond_by_scope(self, scope_id=-1):
        block = self.scope[scope_id].hdl_block
        return self._exit_cond(block)

    @property
    def rst_cond(self):
        if len(self.scope) == 1:
            assert isinstance(self.scope[0].hdl_block, ht.Module)
            block = self.scope[0].hdl_block.stmts
        else:
            block = [s.hdl_block for s in self.scope[1:]]
        return find_exit_cond(block, search_in_cond=True)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()
