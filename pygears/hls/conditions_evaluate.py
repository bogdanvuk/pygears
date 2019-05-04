from .conditions_utils import (add_cond_expr_operands, add_cycle_cond,
                               add_exit_cond, combine_conditions,
                               nested_cycle_cond, nested_exit_cond)
from .hls_expressions import BinOpExpr
from .pydl_types import (CycleSubCond, ExitSubCond, SubConditions,
                         is_container, subcond_expr)
from .scheduling_types import SeqCBlock
from .utils import state_expr


def get_cblock_child(cblock):
    if hasattr(cblock, 'child'):
        yield from cblock.child
    else:
        yield cblock  # Leaf


def get_cblock_pydl_stmts(cblock):
    if hasattr(cblock, 'pydl_block'):
        yield cblock.pydl_block
    else:
        yield from cblock.pydl_blocks


class ConditionsEval:
    def _create_combined(self, sub_cond, stmt, cond):
        if stmt.in_cond is None:
            block_cond = sub_cond
        else:
            if sub_cond is None:
                block_cond = None
            else:
                add_cond_expr_operands(sub_cond)
                block_cond = combine_conditions((sub_cond, stmt.in_cond), '&&')

        if cond is None:
            return block_cond

        if block_cond is None:
            return cond

        return combine_conditions((cond, block_cond), '||')

    def _merge_pydl_conds(self, top, cond_type):
        if all(
            [getattr(stmt, f'{cond_type}_cond') is None
             for stmt in top.stmts]):
            return None

        cond = None
        for stmt in top.stmts:
            sub_cond = None
            if getattr(stmt, f'{cond_type}_cond', None):
                sub_cond = self._pydl_subconds(stmt, cond_type)
            cond = self._create_combined(sub_cond, stmt, cond)
        return cond

    def _merge_cblock_conds(self, top, cond_type):
        cblocks = [x for x in get_cblock_child(top)]

        if all([
                getattr(pydl_stmt, f'{cond_type}_cond') is None
                for child in cblocks
                for pydl_stmt in get_cblock_pydl_stmts(child)
        ]):
            return None

        cond = None
        for child in cblocks:
            for curr_block in get_cblock_pydl_stmts(child):
                sub_cond = getattr(curr_block, f'{cond_type}_cond', None)
                if sub_cond is not None:
                    sub_cond = self._cblock_subconds(sub_cond, child,
                                                     cond_type)
                cond = self._create_combined(sub_cond, curr_block, cond)
        return cond

    def _cblock_simple_cycle_subconds(self, cblock):
        conds = []
        for child in get_cblock_child(cblock):
            for pydl_stmt in get_cblock_pydl_stmts(child):
                if getattr(pydl_stmt, 'cycle_cond', None) is not None:
                    conds.append(nested_cycle_cond(pydl_stmt))
                    add_cycle_cond(pydl_stmt.id)

        return combine_conditions(conds)

    def _cblock_state_cycle_subconds(self, cblock):
        curr_child = cblock.child[-1]
        sub_conds = curr_child.pydl_block.cycle_cond
        if sub_conds is not None:
            add_cycle_cond(curr_child.pydl_block.id)
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
            pydl_stmts = [x for x in get_cblock_pydl_stmts(child)]
            for pydl_stmt in reversed(pydl_stmts):
                if is_container(pydl_stmt):
                    child_exit_cond = self._merge_pydl_conds(pydl_stmt, 'exit')
                else:
                    child_exit_cond = getattr(pydl_stmt, 'exit_cond', None)
                if child_exit_cond is not None:
                    exit_c = nested_exit_cond(pydl_stmt)
                    add_exit_cond(pydl_stmt.id)
                    return subcond_expr(cond, exit_c)

        return subcond_expr(cond, 1)

    def _cblock_subconds(self, cond, cblock, cond_type):
        if cond_type == 'cycle':
            return self._cblock_cycle_subconds(cond, cblock)

        return self._cblock_exit_subconds(cond, cblock)

    def _pydl_stmt_cycle_cond(self, block):
        conds = []
        for stmt in block.stmts:
            sub_cond = self._pydl_cycle_subconds(stmt)
            if sub_cond is not None:
                conds.append(nested_cycle_cond(stmt))
        return combine_conditions(conds)

    def _pydl_stmt_exit_cond(self, block):
        for stmt in reversed(block.stmts):
            exit_c = self._pydl_exit_subconds(stmt)
            if exit_c is not None:
                return exit_c
        return None

    def _subcond_expr(self, cond, block):
        if isinstance(cond, CycleSubCond):
            sub_c = self._pydl_stmt_cycle_cond(block)
        elif isinstance(cond, ExitSubCond):
            sub_c = self._pydl_stmt_exit_cond(block)
        else:
            sub_c = BinOpExpr(
                self._pydl_stmt_cycle_cond(block),
                self._pydl_stmt_exit_cond(block), cond.operator)

        return subcond_expr(cond, sub_c)

    def _pydl_cycle_subconds(self, block):
        if is_container(block):
            return self._merge_pydl_conds(block, 'cycle')

        cond = getattr(block, 'cycle_cond', None)
        if isinstance(cond, SubConditions):
            return self._subcond_expr(cond, block)
        return cond

    def _pydl_exit_subconds(self, block):
        if is_container(block):
            return self._merge_pydl_conds(block, 'exit')

        cond = getattr(block, 'exit_cond', None)
        if isinstance(cond, SubConditions):
            return self._subcond_expr(cond, block)
        return cond

    def _pydl_subconds(self, block, cond_type):
        if cond_type == 'cycle':
            return self._pydl_cycle_subconds(block)
        return self._pydl_exit_subconds(block)

    def in_cond(self, block, scope):
        return block.in_cond

    def cycle_cond(self, block, scope):
        if block != scope.pydl_block:
            # leaf
            return self._pydl_cycle_subconds(block)

        if is_container(block):
            return self._merge_cblock_conds(scope, 'cycle')

        curr_cond = block.cycle_cond
        if not isinstance(curr_cond, SubConditions):
            return curr_cond

        return self._cblock_cycle_subconds(curr_cond, scope)

    def exit_cond(self, block, scope):
        if block != scope.pydl_block:
            # leaf
            return self._pydl_exit_subconds(block)

        if is_container(block):
            return self._merge_cblock_conds(scope, 'exit')

        curr_cond = block.exit_cond
        if not isinstance(curr_cond, SubConditions):
            return curr_cond

        return self._cblock_exit_subconds(curr_cond, scope)
