import re
from functools import reduce
from string import Template

from . import hdl_types as ht
from .hdl_utils import state_expr
from .scheduling_types import SeqCBlock

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

    def _eval_cyclesubcond(self, cond, cblock):
        if isinstance(cblock, SeqCBlock) and len(cblock.state_ids) > 1:
            curr_child = cblock.child[-1]
            sub_conds = curr_child.hdl_block.cycle_cond
            if sub_conds is not None:
                sub_conds = state_expr(curr_child.state_ids, sub_conds)
                self.add_cycle_cond(curr_child.hdl_block.id)
        else:
            conds = []
            for child in cblock.child:
                if child.hdl_block.cycle_cond is not None:
                    conds.append(nested_cycle_cond(child.hdl_block))
                    self.add_cycle_cond(child.hdl_block.id)
            sub_conds = reduce(ht.and_expr, conds, None)

        if cond.expr is not None:
            return ht.binary_expr(cond.expr, sub_conds, cond.operator)

        return sub_conds

    def _eval_exitsubcond(self, cond, block):
        exit_c = None
        for child in reversed(block.child):
            child_exit_cond = getattr(child.hdl_block, 'exit_cond', None)
            if child_exit_cond is not None:
                exit_c = nested_exit_cond(child.hdl_block)
                self.add_exit_cond(child.hdl_block.id)
                break

        if cond.expr is not None:
            if exit_c is not None:
                return ht.binary_expr(cond.expr, exit_c, cond.operator)
            return cond.expr

        return exit_c

    def _eval_subcond(self, cond, cond_type, block):
        if cond_type == 'cycle':
            return self._eval_cyclesubcond(cond, block)

        return self._eval_exitsubcond(cond, block)

    def _merge_conds(self, top, cond_type):
        if all([
                getattr(child.hdl_block, f'{cond_type}_cond') is None
                for child in top.child
        ]):
            return None

        cond = None
        for child in top.child:
            curr_block = child.hdl_block
            sub_cond = getattr(curr_block, f'{cond_type}_cond', None)
            if sub_cond is not None:
                sub_cond = self._eval_subcond(sub_cond, cond_type, child)
            block_cond = ht.and_expr(sub_cond, curr_block.in_cond)
            cond = ht.or_expr(cond, block_cond)
        return cond

    def block_cycle_cond(self, block):
        assert block == self.scope[-1].hdl_block

        if isinstance(block, ht.ContainerBlock):
            return self._merge_conds(self.scope[-1], 'cycle')

        curr_cond = block.cycle_cond
        if not isinstance(curr_cond, ht.CycleSubCond):
            return curr_cond

        return self._eval_cyclesubcond(curr_cond, self.scope[-1])

    def block_exit_cond(self, block):
        assert block == self.scope[-1].hdl_block

        if isinstance(block, ht.ContainerBlock):
            return self._merge_conds(self.scope[-1], 'exit')

        curr_cond = block.exit_cond
        if not isinstance(curr_cond, ht.ExitSubCond):
            return curr_cond

        return self._eval_exitsubcond(curr_cond, self.scope[-1])

    def _create_state_cycle_cond(self, child):
        child_cond = nested_cycle_cond(child.hdl_block.cycle_cond)
        self.add_cycle_cond(find_cond_id(child_cond))
        return state_expr(child.state_ids, child_cond)

    def _state_depend_cycle_cond(self, hdl_block):
        c_block = self.scope[-1]

        if c_block.prolog is not None and hdl_block in c_block.prolog:
            return self._create_state_cycle_cond(c_block.child[0])

        if c_block.epilog is not None and hdl_block in c_block.epilog:
            return self._create_state_cycle_cond(c_block.child[-1])

        for child_idx, child in enumerate(c_block.child):
            if (child.hdl_block == hdl_block) or (child.prolog is not None and
                                                  hdl_block in child.prolog):
                return self._create_state_cycle_cond(child)

            if child.epilog is not None and hdl_block in child.epilog:
                if len(c_block.child) > (child_idx + 1):
                    return self._create_state_cycle_cond(
                        c_block.child[child_idx + 1])

                return self._create_state_cycle_cond(child)

        raise Exception('State dependency but no child found in cycle cond')

    def cycle_cond(self, hdl_block):
        cond = []
        for i, c_block in enumerate(reversed(self.scope[1:])):
            # state changes break the cycle
            if len(c_block.state_ids) > len(self.scope[-1].state_ids):
                break

            if (i == 0) and c_block.hdl_block != hdl_block and len(
                    c_block.state_ids) > 1:
                return self._state_depend_cycle_cond(hdl_block)

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

    def exit_cond(self, hdl_block):
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
