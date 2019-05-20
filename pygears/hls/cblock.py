from .hdl_stmt import CombBlock
from .inst_visit import InstanceVisitor
from .pydl_types import Block
from .utils import add_to_list, state_expr


class CBlockVisitor(InstanceVisitor):
    def __init__(self, hdl_visitor, state_num):
        self.state_num = state_num
        self.hdl = hdl_visitor

    def add_state_conditions(self, cblock, hdl_block):
        if self.state_num == 0 or (not cblock.parent):
            return

        current_ids = cblock.state_ids

        # if in module even exist states other than the ones in this
        # cblock
        if (current_ids != cblock.parent.state_ids) and (current_ids != list(
                range(self.state_num + 1))):
            hdl_block.in_cond = state_expr(current_ids, hdl_block.in_cond)

    def enter_block(self, block, state):
        hdl_block = self.ping_hdl(block.pydl_block, block.conditions['block'])
        if state:
            self.add_state_conditions(block, hdl_block)
        return hdl_block

    def exit_block(self):
        pass

    def visit_prolog(self, node):
        prolog_stmts = []
        if node.prolog:
            cond = node.conditions['prolog']
            for block in node.prolog:
                curr_block = self.ping_hdl(block, cond)
                self._add_sub(block, curr_block, cond)
                add_to_list(prolog_stmts, curr_block)
        return prolog_stmts

    def visit_epilog(self, node):
        epilog = []
        if node.epilog:
            cond = node.conditions['epilog']
            for block in node.epilog:
                curr_block = self.ping_hdl(block, cond)
                self._add_sub(block, curr_block, cond)
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

        self.exit_block()

        add_to_list(top, curr_block)

        add_to_list(top, self.visit_epilog(node))

        if len(top) == 1 and isinstance(top[0], CombBlock):
            return top[0]

        return top

    def visit_SeqCBlock(self, node):
        return self.visit_block(node, True)

    def visit_MutexCBlock(self, node):
        return self.visit_block(node, True)

    def _add_sub(self, block, curr_block, cond):
        if isinstance(block, Block):
            for stmt in block.stmts:
                sub = self.ping_hdl(stmt, cond)
                self._add_sub(stmt, sub, cond)
                add_to_list(curr_block.stmts, sub)
            self.hdl.update_defaults(curr_block)

    def visit_Leaf(self, node):
        hdl_block = []
        cond = node.conditions['leaf']
        for block in node.pydl_blocks:
            curr_block = self.ping_hdl(block, cond)
            self._add_sub(block, curr_block, cond)
            add_to_list(hdl_block, curr_block)
        return hdl_block

    def ping_hdl(self, block, cond):
        return self.hdl.visit(block, cond)


class CBlockPrinter(InstanceVisitor):
    def __init__(self):
        self.indent = 0

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        print(f'{" "*self.indent}{line}')

    def get_pydl(self, node):
        if hasattr(node, 'pydl_blocks'):
            pydl = []
            for block in node.pydl_blocks:
                pydl.append(block.__class__.__name__)
            return pydl

        return node.pydl_block.__class__.__name__

    def generic_visit(self, node):
        if hasattr(node, 'child'):
            self.write_line(
                f'{node.__class__.__name__}: states: {node.state_ids}, ({self.get_pydl(node)})'
            )
            self.enter_block()
            for child in node.child:
                self.visit(child)
            self.exit_block()
        else:
            self.write_line(
                f'Leaf: state {node.state_id}, {self.get_pydl(node)}')


def pprint(node):
    CBlockPrinter().visit(node)
