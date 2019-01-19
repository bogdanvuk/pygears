import hdl_types as ht

from .inst_visit import InstanceVisitor


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

    def enter_block(self, block):
        self.scope.append(block)

        hdl_block = self.hdl.visit(block.hdl_block)

        if self.state_num > 0 and block.parent:
            if block.state_ids != block.parent.state_ids:
                hdl_block.in_cond = state_expr(block.state_ids,
                                               hdl_block.in_cond)

            # state transition injection
            state_transition = list(
                set(block.parent.state_ids) - set(block.state_ids))
            if state_transition and len(block.state_ids) == 1:
                state_copy_block = self.hdl.visit(
                    block.hdl_block, state_id=state_transition[0])
                state_copy_block.in_cond = None  # already in hdl_block
                add_to_list(hdl_block.stmts, state_copy_block)

        return hdl_block

    def exit_block(self):
        self.scope.pop()

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
