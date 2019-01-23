from functools import reduce
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
        self.cycle_conds = []
        self.exit_conds = []

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
            # state_transition = list(
            #     set(cblock.parent.state_ids) - set(current_ids))
            parent_ids = list(set(cblock.parent.state_ids))
            assert len(set(current_ids)) == 1
            curr_index = parent_ids.index(current_ids[0])
            if len(parent_ids) > (curr_index) + 1:
                state_transition = parent_ids[curr_index + 1]
            else:
                state_transition = None
                # for idx in set(cblock.parent.state_ids):

            self._set_conds()
            if state_transition:
                state_copy_block = self.hdl.visit(
                    current_hdl, state_id=state_transition)
                state_copy_block.in_cond = None  # already in hdl_block
                add_to_list(hdl_block.stmts, state_copy_block)

    def enter_block(self, block):
        self.scope.append(block)
        self._set_conds()
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

    def _add_sub(self, block, curr_block):
        if isinstance(block, ht.Block):
            for stmt in block.stmts:
                self._set_conds()
                sub = self.hdl.visit(stmt)
                self._add_sub(stmt, sub)
                add_to_list(curr_block.stmts, sub)
            self.hdl.update_defaults(curr_block)

    def _set_conds(self):
        cycle_cond = []
        for c in reversed(self.scope):
            s = c.hdl_block
            if isinstance(s, ht.ContainerBlock):
                continue

            if s.cycle_cond and s.cycle_cond != 1:
                self.cycle_conds.append(s.id)
                cycle_cond.append(f'cycle_cond_block_{s.id}')

            if hasattr(s, 'multicycle') and s.multicycle:
                break

        cycle_cond = reduce(ht.and_expr, cycle_cond, None)

        exit_cond = []
        for c in reversed(self.scope):
            s = c.hdl_block
            if isinstance(s, ht.ContainerBlock):
                continue

            if s.exit_cond and s.exit_cond != 1:
                self.exit_conds.append(s.id)
                exit_cond.append(f'exit_cond_block_{s.id}')

        exit_cond = reduce(ht.and_expr, exit_cond, None)

        self.hdl.cycle_cond = cycle_cond
        self.hdl.exit_cond = exit_cond

    def visit_Leaf(self, node):
        hdl_block = []
        for i, block in enumerate(node.hdl_blocks):
            self._set_conds()

            curr_block = self.hdl.visit(block)
            self._add_sub(block, curr_block)
            if isinstance(block, ht.Yield):
                # if curr_block.stmts or curr_block.dflts:
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
