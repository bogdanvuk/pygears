from dataclasses import dataclass
from functools import reduce

from . import hdl_types as ht
from .hdl_stmt import CombBlock, HDLBlock
from .hdl_utils import add_to_list, state_expr
from .inst_visit import InstanceVisitor


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


class Conditions:
    def __init__(self):
        self.scope = []
        self.cycle_conds = []
        self.exit_conds = []

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
                cond.append(ht.nested_cycle_cond(block))
                self.cycle_conds.append(ht.find_cond_id(cond[-1]))

            if hasattr(block, 'multicycle') and block.multicycle:
                break

        cond = set(cond)
        return reduce(ht.and_expr, cond, None)

    def _exit_cond(self, block):
        cond = ht.nested_exit_cond(block)
        if cond is not None:
            self.exit_conds.append(ht.find_cond_id(cond))
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
        return ht.find_exit_cond(block, search_in_cond=True)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()


class CBlockVisitor(InstanceVisitor):
    def __init__(self, hdl_visitor, state_num):
        self.hdl = hdl_visitor
        self.state_num = state_num
        self.conds = Conditions()

    @property
    def cycle_conds(self):
        return self.conds.cycle_conds

    @property
    def exit_conds(self):
        return self.conds.exit_conds

    def ping_state_transitions(self, cblock, hdl_block, tr):
        if tr.next_state is not None:
            state_copy_block = self.ping_hdl(
                cblock.hdl_block, state_id=tr.next_state)
            state_copy_block.in_cond = None  # already in hdl_block
            add_to_list(hdl_block.stmts, state_copy_block)
        if tr.cycle_state is not None:
            state_copy_block = self.ping_hdl(
                cblock.hdl_block, state_id=tr.cycle_state)
            state_copy_block.in_cond = None  # already in hdl_block
            add_to_list(hdl_block.stmts, state_copy_block)
        if tr.done_state is not None:
            state_copy_block = self.ping_hdl(
                cblock.hdl_block, state_id=tr.done_state)
            state_copy_block.in_cond = None  # already in hdl_block
            add_to_list(hdl_block.stmts, state_copy_block)

    def find_state_transition(self, cblock):
        curr_id = cblock.state_ids[0]
        parent = cblock.parent
        scope = -1

        trans = StateTransitions()

        parent_ids = list(set(parent.state_ids))
        curr_index = parent_ids.index(curr_id) + 1
        if len(parent_ids) > curr_index:
            trans.next_state = StateTransition(parent_ids[curr_index], scope)
        elif curr_id == parent_ids[-1] and len(
                parent_ids) > 1:  # last to first
            scope -= 1
            trans.cycle_state = StateTransition(parent_ids[0], scope)

        if trans.cycle_state is not None:
            parent = parent.parent
            scope -= 1
            while parent:
                parent_ids = list(set(parent.state_ids))
                curr_index = parent_ids.index(curr_id) + 1
                if len(parent_ids) > curr_index:
                    trans.done_state = StateTransition(parent_ids[curr_index],
                                                       scope)
                    break

                parent = parent.parent
                scope -= 1

        return trans

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
            state_transition = self.find_state_transition(cblock)
            if state_transition.found:
                self.ping_state_transitions(cblock, hdl_block,
                                            state_transition)

    def enter_block(self, block, state):
        self.conds.enter_block(block)
        hdl_block = self.ping_hdl(block.hdl_block)
        if state:
            self.add_state_conditions(block, hdl_block)
        return hdl_block

    def exit_block(self):
        self.conds.exit_block()

    def visit_prolog(self, node):
        prolog_stmts = []
        prolog_block = None
        if node.prolog:
            if node.parent and len(node.parent.state_ids) > len(
                    node.state_ids):
                prolog_block = HDLBlock(
                    in_cond=state_expr(node.state_ids, None),
                    stmts=[],
                    dflts={})

            for block in node.prolog:
                curr_block = self.ping_hdl(block)
                self._add_sub(block, curr_block)
                add_to_list(prolog_stmts, curr_block)

        if prolog_block is not None:
            prolog_block.stmts = prolog_stmts
            return prolog_block

        return prolog_stmts

    def visit_epilog(self, node, epilog_cond):
        epilog = []
        if node.epilog:
            for block in node.epilog:
                curr_block = self.ping_hdl(block, context_cond=epilog_cond)
                self._add_sub(block, curr_block, context_cond=epilog_cond)
                add_to_list(epilog, curr_block)
        return epilog

    def visit_block(self, node, state=True):
        top = []

        add_to_list(top, self.visit_prolog(node))

        curr_block = self.enter_block(node, state)

        for child in node.child:
            add_to_list(curr_block.stmts, self.visit(child))

        if curr_block.stmts:
            self.hdl.update_defaults(curr_block)

        epilog_cond = self.conds.rst_cond if node.epilog else None

        self.exit_block()

        add_to_list(top, curr_block)

        add_to_list(top, self.visit_epilog(node, epilog_cond))

        if len(top) == 1 and isinstance(top[0], CombBlock):
            return top[0]

        return top

    def visit_SeqCBlock(self, node):
        return self.visit_block(node, True)

    def visit_MutexCBlock(self, node):
        return self.visit_block(node, False)

    def _add_sub(self, block, curr_block, **kwds):
        if isinstance(block, ht.Block):
            for stmt in block.stmts:
                sub = self.ping_hdl(stmt, **kwds)
                self._add_sub(stmt, sub, **kwds)
                add_to_list(curr_block.stmts, sub)
            self.hdl.update_defaults(curr_block)

    def visit_Leaf(self, node):
        hdl_block = []
        for block in node.hdl_blocks:
            curr_block = self.ping_hdl(block)
            self._add_sub(block, curr_block)
            add_to_list(hdl_block, curr_block)
        return hdl_block

    def ping_hdl(self, block, **kwds):
        return self.hdl.visit(block, conds=self.conds, **kwds)


class CBlockPrinter(InstanceVisitor):
    def __init__(self):
        self.indent = 0

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        print(f'{" "*self.indent}{line}')

    def get_hdl(self, node):
        if hasattr(node, 'hdl_blocks'):
            hdl = []
            for block in node.hdl_blocks:
                hdl.append(block.__class__.__name__)
            return hdl

        return node.hdl_block.__class__.__name__

    def generic_visit(self, node):
        if hasattr(node, 'child'):
            self.write_line(
                f'{node.__class__.__name__}: states: {node.state_ids}, ({self.get_hdl(node)})'
            )
            self.enter_block()
            for child in node.child:
                self.visit(child)
            self.exit_block()
        else:
            self.write_line(
                f'Leaf: state {node.state_id}, {self.get_hdl(node)}')


def pprint(node):
    CBlockPrinter().visit(node)
