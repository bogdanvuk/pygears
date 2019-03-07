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


class ConditionsBase:
    # shared across all visitors
    cycle_conds = []
    exit_conds = []
    combined_cycle_conds = {}
    combined_exit_conds = {}

    def add_cycle_cond(self, cond):
        assert cond is not None, 'Attempting to add None id to cycle conditions'

        if cond not in self.cycle_conds:
            self.cycle_conds.append(cond)

    def add_exit_cond(self, cond):
        assert cond is not None, 'Attempting to add None id to exit conditions'

        if cond not in self.exit_conds:
            self.exit_conds.append(cond)


class ConditionsFinder(ConditionsBase):
    def __init__(self):
        self.scope = []

    def _create_state_cycle_cond(self, child):
        child_cond = nested_cycle_cond(child.hdl_block)
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

    def exit_cond_by_scope(self, scope_id=-1):
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


def get_cblock_child(cblock):
    if hasattr(cblock, 'child'):
        yield from cblock.child
    else:
        yield cblock  # Leaf


def get_cblock_hdl_stmts(cblock):
    if hasattr(cblock, 'hdl_block'):
        yield cblock.hdl_block
    else:
        yield from cblock.hdl_blocks


class ConditionsEval(ConditionsBase):
    def _merge_hdl_conds(self, top, cond_type):
        if all(
            [getattr(stmt, f'{cond_type}_cond') is None
             for stmt in top.stmts]):
            return None

        cond = None
        for stmt in top.stmts:
            sub_cond = None
            if getattr(stmt, f'{cond_type}_cond', None):
                sub_cond = self._hdl_subconds(stmt, cond_type)
            block_cond = ht.and_expr(sub_cond, stmt.in_cond)
            cond = ht.or_expr(cond, block_cond)
        return cond

    def _merge_cblock_conds(self, top, cond_type):
        cblocks = [x for x in get_cblock_child(top)]

        if all([
                getattr(hdl_stmt, f'{cond_type}_cond') is None
                for child in cblocks
                for hdl_stmt in get_cblock_hdl_stmts(child)
        ]):
            return None

        cond = None
        for child in cblocks:
            for curr_block in get_cblock_hdl_stmts(child):
                sub_cond = getattr(curr_block, f'{cond_type}_cond', None)
                if sub_cond is not None:
                    sub_cond = self._cblock_subconds(sub_cond, child,
                                                     cond_type)
                block_cond = ht.and_expr(sub_cond, curr_block.in_cond)
                cond = ht.or_expr(cond, block_cond)
        return cond

    def _cblock_simple_cycle_subconds(self, cblock):
        conds = []
        for child in get_cblock_child(cblock):
            for hdl_stmt in get_cblock_hdl_stmts(child):
                if hdl_stmt.cycle_cond is not None:
                    conds.append(nested_cycle_cond(hdl_stmt))
                    self.add_cycle_cond(hdl_stmt.id)

        return reduce(ht.and_expr, conds, None)

    def _cblock_state_cycle_subconds(self, cblock):
        curr_child = cblock.child[-1]
        sub_conds = curr_child.hdl_block.cycle_cond
        if sub_conds is not None:
            self.add_cycle_cond(curr_child.hdl_block.id)
            sub_conds = state_expr(curr_child.state_ids, sub_conds)

        return sub_conds

    def _cblock_cycle_subconds(self, cond, cblock):
        if isinstance(cblock, SeqCBlock) and len(cblock.state_ids) > 1:
            sub_conds = self._cblock_state_cycle_subconds(cblock)
        else:
            sub_conds = self._cblock_simple_cycle_subconds(cblock)

        return ht.subcond_expr(cond, sub_conds)

    def _cblock_exit_subconds(self, cond, cblock):
        exit_c = None
        children = [x for x in get_cblock_child(cblock)]
        for child in reversed(children):
            hdl_stmts = [x for x in get_cblock_hdl_stmts(child)]
            for hdl_stmt in reversed(hdl_stmts):
                if isinstance(hdl_stmt, ht.ContainerBlock):
                    child_exit_cond = self._merge_hdl_conds(hdl_stmt, 'exit')
                else:
                    child_exit_cond = getattr(hdl_stmt, 'exit_cond', None)
                if child_exit_cond is not None:
                    exit_c = nested_exit_cond(hdl_stmt)
                    self.add_exit_cond(hdl_stmt.id)
                    break

        return ht.subcond_expr(cond, exit_c)

    def _cblock_subconds(self, cond, cblock, cond_type):
        if cond_type == 'cycle':
            return self._cblock_cycle_subconds(cond, cblock)

        return self._cblock_exit_subconds(cond, cblock)

    def _hdl_stmt_cycle_cond(self, block):
        conds = []
        for stmt in block.stmts:
            sub_cond = self._hdl_cycle_subconds(stmt)
            if sub_cond is not None:
                conds.append(nested_cycle_cond(stmt))
        return reduce(ht.and_expr, conds, None)

    def _hdl_stmt_exit_cond(self, block):
        for stmt in reversed(block.stmts):
            exit_c = self._hdl_exit_subconds(stmt)
            if exit_c is not None:
                return exit_c
        return None

    def _subcond_expr(self, cond, block):
        if isinstance(cond, ht.CycleSubCond):
            sub_c = self._hdl_stmt_cycle_cond(block)
        else:
            sub_c = self._hdl_stmt_exit_cond(block)

        return ht.subcond_expr(cond, sub_c)

    def _hdl_cycle_subconds(self, block):
        if isinstance(block, ht.ContainerBlock):
            return self._merge_hdl_conds(block, 'cycle')

        cond = getattr(block, 'cycle_cond', None)
        if isinstance(cond, ht.SubConditions):
            return self._subcond_expr(cond, block)
        return cond

    def _hdl_exit_subconds(self, block):
        if isinstance(block, ht.ContainerBlock):
            return self._merge_hdl_conds(block, 'exit')

        cond = getattr(block, 'exit_cond', None)
        if isinstance(cond, ht.SubConditions):
            return self._subcond_expr(cond, block)
        return cond

    def _hdl_subconds(self, block, cond_type):
        if cond_type == 'cycle':
            return self._hdl_cycle_subconds(block)
        return self._hdl_exit_subconds(block)

    def cycle_cond(self, block, scope):
        if block != scope.hdl_block:
            # leaf
            return self._hdl_cycle_subconds(block)

        if isinstance(block, ht.ContainerBlock):
            return self._merge_cblock_conds(scope, 'cycle')

        curr_cond = block.cycle_cond
        if not isinstance(curr_cond, ht.CycleSubCond):
            return curr_cond

        return self._cblock_cycle_subconds(curr_cond, scope)

    def exit_cond(self, block, scope):
        if block != scope.hdl_block:
            # leaf
            return self._hdl_exit_subconds(block)

        if isinstance(block, ht.ContainerBlock):
            return self._merge_cblock_conds(scope, 'exit')

        curr_cond = block.exit_cond
        if not isinstance(curr_cond, ht.ExitSubCond):
            return curr_cond

        return self._cblock_exit_subconds(curr_cond, scope)


class Conditions(ConditionsBase):
    def __init__(self):
        self.scope = []
        self.cond_finder = ConditionsFinder()
        self.cond_eval = ConditionsEval()

    def enter_block(self, block):
        self.scope.append(block)
        self.cond_finder.enter_block(block)

    def exit_block(self):
        self.cond_finder.exit_block()
        self.scope.pop()

    @property
    def rst_cond(self):
        return self.cond_finder.rst_cond

    def find_cycle_cond(self, hdl_block):
        return self.cond_finder.cycle_cond(hdl_block)

    def find_exit_cond(self, hdl_block):
        return self.cond_finder.exit_cond(hdl_block)

    def find_exit_cond_by_scope(self, scope_id=-1):
        return self.cond_finder.exit_cond_by_scope(scope_id)

    def eval_cycle_cond(self, block):
        return self.cond_eval.cycle_cond(block, self.scope[-1])

    def eval_exit_cond(self, block):
        return self.cond_eval.exit_cond(block, self.scope[-1])
