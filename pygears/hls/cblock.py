from . import hdl_types as ht
from .hdl_stmt import CombBlock
from .hdl_utils import add_to_list, state_expr
from .inst_visit import InstanceVisitor
from .scheduling_types import MutexCBlock


class CBlockVisitor(InstanceVisitor):
    def __init__(self, hdl_visitor, state_num):
        self.hdl = hdl_visitor
        self.state_num = state_num
        self.conds = ht.Conditions()

    @property
    def cycle_conds(self):
        return self.conds.cycle_conds

    @property
    def exit_conds(self):
        return self.conds.exit_conds

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
            state_transition = None

            while state_transition is None:
                parent = cblock.parent
                if not parent:
                    break

                parent_ids = list(set(parent.state_ids))
                curr_index = parent_ids.index(current_ids[0]) + 1

                if len(parent_ids) > curr_index:
                    state_transition = parent_ids[curr_index]
                    visit_hdl = cblock.hdl_block
                elif current_ids[0] == parent_ids[-1]:  # last to first
                    state_transition = parent_ids[0]
                    visit_hdl = parent.hdl_block

                if state_transition is not None:
                    state_copy_block = self.ping_hdl(
                        visit_hdl, state_id=state_transition)
                    state_copy_block.in_cond = None  # already in hdl_block
                    add_to_list(hdl_block.stmts, state_copy_block)

                cblock = parent

    def enter_block(self, block, state):
        self.conds.enter_block(block)
        hdl_block = self.ping_hdl(block.hdl_block)
        if state:
            self.add_state_conditions(block, hdl_block)
        return hdl_block

    def exit_block(self):
        self.conds.exit_block()

    def visit_prolog(self, node):
        prolog = []
        if node.prolog:
            for block in node.prolog:
                curr_block = self.ping_hdl(block)
                self._add_sub(block, curr_block)
                add_to_list(prolog, curr_block)
        return prolog

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
