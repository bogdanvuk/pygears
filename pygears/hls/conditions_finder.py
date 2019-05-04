from dataclasses import dataclass
from enum import IntEnum

from .conditions_utils import (combine_conditions, find_exit_cond,
                               nested_cycle_cond, nested_exit_cond)
from .inst_visit import InstanceVisitor
from .pydl_types import Module, is_container
from .utils import state_expr


@dataclass
class BlockCondtitions:
    cycle_cond = None
    exit_cond = None


class BlockType(IntEnum):
    leaf = 0
    prolog = 1
    epilog = 2
    block = 3


def create_state_cycle_cond(child):
    child_cond = nested_cycle_cond(child.pydl_block)
    return state_expr(child.state_ids, child_cond)


class ConditionsFinder(InstanceVisitor):
    def __init__(self, state_num):
        self.state_num = state_num
        self.scope = []

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def visit_block(self, node):
        if node.prolog:
            self._add_conditions(node, BlockType.prolog)

        self.enter_block(node)

        self._add_conditions(node, BlockType.block)

        for child in node.child:
            self.visit(child)

        epilog_cond = self.get_rst_cond() if node.epilog else None

        self.exit_block()

        if node.epilog:
            self._add_conditions(node, BlockType.epilog, epilog_cond)

    def visit_SeqCBlock(self, node):
        self.visit_block(node)

    def visit_MutexCBlock(self, node):
        self.visit_block(node)

    def visit_Leaf(self, node):
        self._add_conditions(node, BlockType.leaf)

    def _add_conditions(self, node, block_type, added_cond=None):
        cond = BlockCondtitions()
        cycle_cond = self.get_cycle_cond(block_type)
        exit_cond = self.get_exit_cond()

        if added_cond is None:
            cond.cycle_cond = cycle_cond
            cond.exit_cond = exit_cond
        else:
            cond.cycle_cond = combine_conditions((cycle_cond, added_cond))
            cond.exit_cond = combine_conditions((exit_cond, added_cond))

        if not hasattr(node, 'conditions'):
            node.conditions = {}

        node.conditions[block_type.name] = cond

    def get_cycle_cond(self, block_type):
        cond = []
        for c_block in reversed(self.scope[1:]):
            # state changes break the cycle
            if len(c_block.state_ids) > len(self.scope[-1].state_ids):
                break

            if block_type != BlockType.block and len(c_block.state_ids) > 1:
                return self._state_depend_cycle_cond(block_type)

            block = c_block.pydl_block
            if is_container(block):
                continue

            if block.cycle_cond and block.cycle_cond != 1:
                cond.append(nested_cycle_cond(block))

            if hasattr(block, 'multicycle') and block.multicycle:
                break

        cond = list(set(cond))
        return combine_conditions(cond)

    def get_exit_cond(self):
        return nested_exit_cond(self.scope[-1].pydl_block)

    def get_rst_cond(self):
        if len(self.scope) == 1:
            assert isinstance(self.scope[0].pydl_block, Module)
            block = self.scope[0].pydl_block.stmts
        else:
            block = [s.pydl_block for s in self.scope[1:]]
        return find_exit_cond(block, search_in_cond=True)

    def _state_depend_cycle_cond(self, block_type):
        c_block = self.scope[-1]

        if block_type == BlockType.prolog:
            return create_state_cycle_cond(c_block.child[0])

        if block_type == BlockType.epilog:
            return create_state_cycle_cond(c_block.child[-1])

        raise Exception('State dependency but prolog/epilog in cycle cond')
