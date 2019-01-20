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

    def add_state_conditions(self, cblock, hdl_block, sub_idx=None):
        if hasattr(cblock, 'state_ids'):
            # Seq or Mutex
            current_ids = cblock.state_ids
            current_hdl = cblock.hdl_block
        else:
            # Leaf
            current_ids = [cblock.state_id]
            current_hdl = cblock.hdl_blocks[sub_idx]

        if self.state_num > 0 and cblock.parent:
            if current_ids != cblock.parent.state_ids:
                hdl_block.in_cond = state_expr(current_ids, hdl_block.in_cond)

            # state transition injection
            state_transition = list(
                set(cblock.parent.state_ids) - set(current_ids))
            if state_transition and len(current_ids) == 1:
                state_copy_block = self.hdl.visit(
                    current_hdl, state_id=state_transition[0])
                state_copy_block.in_cond = None  # already in hdl_block
                add_to_list(hdl_block.stmts, state_copy_block)

    def enter_block(self, block):
        self.scope.append(block)
        hdl_block = self.hdl.visit(block.hdl_block)
        self.add_state_conditions(block, hdl_block)
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
        for i, block in enumerate(node.hdl_blocks):
            curr_block = self.hdl.visit(block)
            if isinstance(block, ht.Block):
                for stmt in block.stmts:
                    add_to_list(curr_block.stmts, self.hdl.visit(stmt))
            if isinstance(block, ht.Yield):
                if curr_block.stmts or curr_block.dflts:
                    self.add_state_conditions(node, curr_block, i)
                    self.hdl.update_defaults(curr_block)
            add_to_list(hdl_block, curr_block)
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
