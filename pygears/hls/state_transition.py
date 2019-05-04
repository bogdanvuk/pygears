from dataclasses import dataclass

from .conditions_utils import add_cond
from .hdl_stmt import find_in_cond, update_hdl_block
from .hdl_types import AssignValue, CombBlock, HDLBlock
from .inst_visit import InstanceVisitor
from .pydl_types import Module
from .scheduling_types import MutexCBlock
from .utils import add_to_list, state_expr


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


def find_exit_cond_by_scope(node, scope):
    curr_node = node
    cnt = scope + 1
    while cnt:
        curr_node = curr_node.parent
        cnt += 1

    if hasattr(curr_node, 'conditions'):
        return curr_node.conditions['block'].exit_cond

    return None


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


def create_hdl_block(node):
    return HDLBlock(in_cond=find_in_cond(node), stmts=[], dflts={})


def create_state_hdl_block(block, state_tr):
    hdl_block = create_hdl_block(block)

    cond = state_tr.scope_exit_cond
    if cond is not None:
        add_cond(cond)

    add_to_list(
        hdl_block.stmts,
        HDLBlock(
            in_cond=cond,
            stmts=[AssignValue(target=f'state_en', val=1)],
            dflts={
                'state_next':
                AssignValue(target='state_next', val=state_tr.next_state)
            }))

    if hdl_block.stmts:
        update_hdl_block(hdl_block)

    return hdl_block


class HdlStmtStateTransition(InstanceVisitor):
    def __init__(self, state_num):
        self.state_num = state_num

    def visit_Leaf(self, node):
        pass

    def visit_children(self, node, hdl_block):
        for child in node.child:
            add_to_list(hdl_block.stmts, self.visit(child))

        if hdl_block.stmts:
            update_hdl_block(hdl_block)

        return hdl_block

    def visit_SeqCBlock(self, node):
        if isinstance(node.pydl_block, Module):
            hdl_block = CombBlock(
                stmts=[], dflts={'state_en': AssignValue(f'state_en', 0)})
        else:
            hdl_block = create_hdl_block(node.pydl_block)

        self.add_state_conditions(node, hdl_block)

        return self.visit_children(node, hdl_block)

    def visit_MutexCBlock(self, node):
        hdl_block = create_hdl_block(node.pydl_block)
        return self.visit_children(node, hdl_block)

    def _add_state_block(self, cblock, hdl_block, state_tr):
        state_tr.scope_exit_cond = find_exit_cond_by_scope(
            cblock, state_tr.scope)
        state_copy_block = create_state_hdl_block(cblock.pydl_block, state_tr)
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
