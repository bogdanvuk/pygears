from .conditions_utils import (ConditionsBase, nested_cycle_cond,
                               nested_exit_cond)
from .hls_blocks import (ContainerBlock, CycleSubCond, ExitSubCond,
                         SubConditions, subcond_expr)
from .hls_expressions import BinOpExpr
from .scheduling_types import SeqCBlock
from .utils import state_expr


def get_cblock_child(cblock):
    if hasattr(cblock, 'child'):
        yield from cblock.child
    else:
        yield cblock  # Leaf


def get_cblock_hdl_stmts(cblock):
    if hasattr(cblock, 'hdl_block'):
        yield cblock.hdl_block
    else:
        yield from cblock.hdl_blocks


class ConditionsEval(ConditionsBase):
    def _create_combined(self, sub_cond, stmt, cond):
        if stmt.in_cond is None:
            block_cond = sub_cond
        else:
            block_cond = self.combine_conditions((sub_cond, stmt.in_cond),
                                                 '&&')

        if cond is None:
            return block_cond

        return self.combine_conditions((cond, block_cond), '||')

    def _merge_hdl_conds(self, top, cond_type):
        if all(
            [getattr(stmt, f'{cond_type}_cond') is None
             for stmt in top.stmts]):
            return None

        cond = None
        for stmt in top.stmts:
            sub_cond = None
            if getattr(stmt, f'{cond_type}_cond', None):
                sub_cond = self._hdl_subconds(stmt, cond_type)
            cond = self._create_combined(sub_cond, stmt, cond)
        return cond

    def _merge_cblock_conds(self, top, cond_type):
        cblocks = [x for x in get_cblock_child(top)]

        if all([
                getattr(hdl_stmt, f'{cond_type}_cond') is None
                for child in cblocks
                for hdl_stmt in get_cblock_hdl_stmts(child)
        ]):
            return None

        cond = None
        for child in cblocks:
            for curr_block in get_cblock_hdl_stmts(child):
                sub_cond = getattr(curr_block, f'{cond_type}_cond', None)
                if sub_cond is not None:
                    sub_cond = self._cblock_subconds(sub_cond, child,
                                                     cond_type)
                cond = self._create_combined(sub_cond, curr_block, cond)
        return cond

    def _cblock_simple_cycle_subconds(self, cblock):
        conds = []
        for child in get_cblock_child(cblock):
            for hdl_stmt in get_cblock_hdl_stmts(child):
                if getattr(hdl_stmt, 'cycle_cond', None) is not None:
                    conds.append(nested_cycle_cond(hdl_stmt))
                    self.add_cycle_cond(hdl_stmt.id)

        return self.combine_conditions(conds)

    def _cblock_state_cycle_subconds(self, cblock):
        curr_child = cblock.child[-1]
        sub_conds = curr_child.hdl_block.cycle_cond
        if sub_conds is not None:
            self.add_cycle_cond(curr_child.hdl_block.id)
            sub_conds = state_expr(curr_child.state_ids, sub_conds)

        return sub_conds

    def _cblock_cycle_subconds(self, cond, cblock):
        if isinstance(cblock, SeqCBlock) and len(cblock.state_ids) > 1:
            sub_conds = self._cblock_state_cycle_subconds(cblock)
        else:
            sub_conds = self._cblock_simple_cycle_subconds(cblock)

        return subcond_expr(cond, sub_conds)

    def _cblock_exit_subconds(self, cond, cblock):
        exit_c = None
        children = [x for x in get_cblock_child(cblock)]
        for child in reversed(children):
            hdl_stmts = [x for x in get_cblock_hdl_stmts(child)]
            for hdl_stmt in reversed(hdl_stmts):
                if isinstance(hdl_stmt, ContainerBlock):
                    child_exit_cond = self._merge_hdl_conds(hdl_stmt, 'exit')
                else:
                    child_exit_cond = getattr(hdl_stmt, 'exit_cond', None)
                if child_exit_cond is not None:
                    exit_c = nested_exit_cond(hdl_stmt)
                    self.add_exit_cond(hdl_stmt.id)
                    return subcond_expr(cond, exit_c)

        return subcond_expr(cond, 1)

    def _cblock_subconds(self, cond, cblock, cond_type):
        if cond_type == 'cycle':
            return self._cblock_cycle_subconds(cond, cblock)

        return self._cblock_exit_subconds(cond, cblock)

    def _hdl_stmt_cycle_cond(self, block):
        conds = []
        for stmt in block.stmts:
            sub_cond = self._hdl_cycle_subconds(stmt)
            if sub_cond is not None:
                conds.append(nested_cycle_cond(stmt))
        return self.combine_conditions(conds)

    def _hdl_stmt_exit_cond(self, block):
        for stmt in reversed(block.stmts):
            exit_c = self._hdl_exit_subconds(stmt)
            if exit_c is not None:
                return exit_c
        return None

    def _subcond_expr(self, cond, block):
        if isinstance(cond, CycleSubCond):
            sub_c = self._hdl_stmt_cycle_cond(block)
        elif isinstance(cond, ExitSubCond):
            sub_c = self._hdl_stmt_exit_cond(block)
        else:
            sub_c = BinOpExpr(
                self._hdl_stmt_cycle_cond(block),
                self._hdl_stmt_exit_cond(block), cond.operator)

        return subcond_expr(cond, sub_c)

    def _hdl_cycle_subconds(self, block):
        if isinstance(block, ContainerBlock):
            return self._merge_hdl_conds(block, 'cycle')

        cond = getattr(block, 'cycle_cond', None)
        if isinstance(cond, SubConditions):
            return self._subcond_expr(cond, block)
        return cond

    def _hdl_exit_subconds(self, block):
        if isinstance(block, ContainerBlock):
            return self._merge_hdl_conds(block, 'exit')

        cond = getattr(block, 'exit_cond', None)
        if isinstance(cond, SubConditions):
            return self._subcond_expr(cond, block)
        return cond

    def _hdl_subconds(self, block, cond_type):
        if cond_type == 'cycle':
            return self._hdl_cycle_subconds(block)
        return self._hdl_exit_subconds(block)

    def in_cond(self, block, scope):
        return block.in_cond

    def cycle_cond(self, block, scope):
        if block != scope.hdl_block:
            # leaf
            return self._hdl_cycle_subconds(block)

        if isinstance(block, ContainerBlock):
            return self._merge_cblock_conds(scope, 'cycle')

        curr_cond = block.cycle_cond
        if not isinstance(curr_cond, SubConditions):
            return curr_cond

        return self._cblock_cycle_subconds(curr_cond, scope)

    def exit_cond(self, block, scope):
        if block != scope.hdl_block:
            # leaf
            return self._hdl_exit_subconds(block)

        if isinstance(block, ContainerBlock):
            return self._merge_cblock_conds(scope, 'exit')

        curr_cond = block.exit_cond
        if not isinstance(curr_cond, SubConditions):
            return curr_cond

        return self._cblock_exit_subconds(curr_cond, scope)
