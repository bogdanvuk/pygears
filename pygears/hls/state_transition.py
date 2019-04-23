from dataclasses import dataclass

from .conditions import Conditions
from .hdl_stmt import HDLStmtVisitor
from .hdl_stmt_types import AssignValue, HDLBlock
from .inst_visit import InstanceVisitor
from .scheduling_types import MutexCBlock
from .utils import add_to_list, state_expr


class HdlStateTransition(HDLStmtVisitor):
    def enter_Module(self, block, **kwds):
        return AssignValue(f'state_en', 0)

    def visit_all_Block(self, node, **kwds):
        block = super().visit_all_Block(node, **kwds)
        if 'state_id' not in kwds:
            return block

        return self.assign_states(block, **kwds)

    def assign_states(self, block, **kwds):
        state_tr = kwds['state_id']

        cond = self.conds.find_exit_cond_by_scope(state_tr.scope)
        if cond is None:
            cond = 1

        add_to_list(
            block.stmts,
            HDLBlock(
                in_cond=cond,
                stmts=[AssignValue(target=f'state_en', val=1)],
                dflts={
                    'state_next':
                    AssignValue(target='state_next', val=state_tr.next_state)
                }))

        if block.stmts:
            self.update_defaults(block)

        return block


@dataclass
class StateTransition:
    next_state: int = None
    scope: int = -1


@dataclass
class StateTransitions:
    next_state: StateTransition = None
    cycle_state: StateTransition = None
    done_state: StateTransition = None

    @property
    def found(self):
        return (self.next_state is not None) or (
            self.cycle_state is not None) or (self.done_state is not None)


def find_done_seqcblock(cblock):
    parent = cblock.parent.parent
    scope = -3  # first parent at -1, last to first is -2
    curr_id = cblock.state_ids[0]

    while parent:
        parent_ids = list(set(parent.state_ids))
        curr_index = parent_ids.index(curr_id) + 1
        if len(parent_ids) > curr_index:
            return StateTransition(parent_ids[curr_index], scope)

        parent = parent.parent
        scope -= 1


def find_done_mutexcblock(cblock):
    parent = cblock.parent
    scope = -1
    parent_ids = list(set(parent.state_ids))

    if (len(parent_ids) == 1) and isinstance(parent, MutexCBlock):
        while isinstance(parent, MutexCBlock):
            last_mutex_parent = parent
            parent = parent.parent
            scope -= 1

        last_mutex_parent = parent
        parent = parent.parent
        scope -= 1

        seq_parent_ids = list(set(parent.state_ids))
        mutex_parent_ids = list(set(last_mutex_parent.state_ids))
        diff_ids = set(seq_parent_ids).symmetric_difference(
            set(mutex_parent_ids))
        diff_ids = list(diff_ids)

        if diff_ids:
            return StateTransition(diff_ids[0], scope - 1)

    return None


def find_state_transition(cblock):
    trans = StateTransitions()

    curr_id = cblock.state_ids[0]
    parent = cblock.parent
    scope = -1

    parent_ids = list(set(parent.state_ids))
    curr_index = parent_ids.index(curr_id) + 1

    if len(parent_ids) > curr_index:
        trans.next_state = StateTransition(parent_ids[curr_index], scope)
    elif curr_id == parent_ids[-1] and len(parent_ids) > 1:  # last to first
        scope -= 1
        trans.cycle_state = StateTransition(parent_ids[0], scope)

    if trans.cycle_state is not None:
        trans.done_state = find_done_seqcblock(cblock)

    if not trans.found:
        trans.done_state = find_done_mutexcblock(cblock)

    return trans


class CBlockStateTransition(InstanceVisitor):
    def __init__(self, module_data, state_num):
        self.state_num = state_num
        self.module_data = module_data
        self.hdl = HdlStateTransition(module_data)

        # TODO : remove after refactor
        self.conds = Conditions()
        self.hdl.conds = self.conds

    def visit_Leaf(self, node):
        pass

    def visit_SeqCBlock(self, node):
        self.conds.enter_block(node)  # TODO

        hdl_block = self.ping_hdl(node.hdl_block)
        self.add_state_conditions(node, hdl_block)
        for child in node.child:
            add_to_list(hdl_block.stmts, self.visit(child))

        self.conds.exit_block()  # TODO

        return hdl_block

    def visit_MutexCBlock(self, node):
        self.conds.enter_block(node)  # TODO

        hdl_block = self.ping_hdl(node.hdl_block)
        for child in node.child:
            add_to_list(hdl_block.stmts, self.visit(child))

        self.conds.exit_block()  # TODO

        return hdl_block

    def ping_hdl(self, block, **kwds):
        return self.hdl.visit(block, **kwds)

    def _add_state_block(self, cblock, hdl_block, state_tr):
        state_copy_block = self.ping_hdl(cblock.hdl_block, state_id=state_tr)
        state_copy_block.in_cond = None  # already in hdl_block
        add_to_list(hdl_block.stmts, state_copy_block)

    def _ping_state_transitions(self, cblock, hdl_block, trans):
        if trans.next_state is not None:
            self._add_state_block(cblock, hdl_block, trans.next_state)
        if trans.cycle_state is not None:
            self._add_state_block(cblock, hdl_block, trans.cycle_state)
        if trans.done_state is not None:
            self._add_state_block(cblock, hdl_block, trans.done_state)

    def add_state_conditions(self, cblock, hdl_block):
        if self.state_num == 0 or (not cblock.parent):
            return

        current_ids = cblock.state_ids

        # if in module even exist states other than the ones in this
        # cblock
        if (current_ids != cblock.parent.state_ids) and (current_ids != list(
                range(self.state_num + 1))):
            hdl_block.in_cond = state_expr(current_ids, hdl_block.in_cond)

        if len(current_ids) == 1:
            state_transition = find_state_transition(cblock)
            if state_transition.found:
                self._ping_state_transitions(cblock, hdl_block,
                                             state_transition)
