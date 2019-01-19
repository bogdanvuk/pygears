from .inst_visit import InstanceVisitor
from .scheduling import SeqCBlock, MutexCBlock, Leaf
import hdl_types as ht


def add_to_list(orig_list, extention):
    if extention:
        orig_list.extend(
            extention if isinstance(extention, list) else [extention])


def get_state_cond(id):
    return ht.BinOpExpr(('state_reg', id), '==')


def state_expr(state_ids, prev_cond):
    state_cond = get_state_cond(state_ids[0])
    for id in state_ids[1:]:
        state_cond = ht.or_expr(state_cond, get_state_cond(id))

    if prev_cond is not None:
        return ht.and_expr(prev_cond, state_cond)
    else:
        return state_cond


class CBlockVisitor(InstanceVisitor):
    def __init__(self, hdl_visitor, state_num):
        self.hdl = hdl_visitor
        self.state_num = state_num
        self.scope = []
        self.hdl_scope = []

    @property
    def current_hdl_block(self):
        return self.hdl_scope[-1]

    def enter_block(self, block):
        self.scope.append(block)
        b = self.hdl.visit(block.hdl_block)
        if self.state_num > 0 and block.parent:
            if block.state_ids != block.parent.state_ids:
                b.in_cond = state_expr(block.state_ids, b.in_cond)
        self.hdl_scope.append(b)
        return b

    def exit_block(self):
        self.scope.pop()
        self.hdl_scope.pop()

    def visit_block(self, node):
        block = self.enter_block(node)

        for i, c in enumerate(node.child):
            add_to_list(block.stmts, self.visit(c))

        if block.stmts:
            self.hdl.update_defaults(block)

        self.exit_block()

        return block

    def visit_SeqCBlock(self, node):
        return self.visit_block(node)

    def visit_MutexCBlock(self, node):
        return self.visit_block(node)

    def visit_Leaf(self, node):
        hdl_block = []
        for block in node.hdl_blocks:
            add_to_list(hdl_block, self.hdl.visit(block))
        return hdl_block


class CBlockPrinter(InstanceVisitor):
    def __init__(self):
        self.indent = 0

    def enter_block(self, block):
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
        else:
            return node.hdl_block.__class__.__name__

    def generic_visit(self, node):
        if hasattr(node, 'child'):
            self.write_line(
                f'{node.__class__.__name__}: states: {node.state_ids}, ({self.get_hdl(node)})'
            )
            self.enter_block(node)
            for c in node.child:
                self.visit(c)
            self.exit_block()
        else:
            self.write_line(
                f'Leaf: state {node.state_id}, {self.get_hdl(node)}')


def pprint(node):
    CBlockPrinter().visit(node)
