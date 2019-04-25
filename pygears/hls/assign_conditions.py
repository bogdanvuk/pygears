from .conditions_evaluate import ConditionsEval
from .conditions_utils import (COMBINED_COND_NAME, COND_NAME, UsedConditions,
                               add_cond, add_cond_expr_operands, find_rst_cond)
from .hdl_types import AssignValue, CombSeparateStmts
from .inst_visit import InstanceVisitor
from .pydl_types import Block, Module
from .utils import state_expr


class AssignConditions(InstanceVisitor):
    def __init__(self, module_data, state_num):
        self.state_num = state_num
        self.has_registers = len(module_data.regs) > 0
        self.cond_types = ['in', 'cycle', 'exit']
        self.cond_eval = ConditionsEval()
        self.condition_assigns = CombSeparateStmts(stmts=[])

        for combined_id in UsedConditions.combined_conds:
            add_cond_expr_operands(
                UsedConditions.values_of_combined[combined_id])

    def get_condition_block(self):
        for combined_id in UsedConditions.combined_conds:
            self._add_stmt(
                AssignValue(
                    target=COMBINED_COND_NAME.substitute(cond_id=combined_id),
                    val=UsedConditions.values_of_combined[combined_id]))
        return self.condition_assigns

    def _add_stmt(self, stmt):
        if stmt not in self.condition_assigns.stmts:
            self.condition_assigns.stmts.append(stmt)

    def _get_cond_by_type(self, cond_type, cnode, pydl_block):
        all_conds = getattr(UsedConditions, f'{cond_type}_conds')
        if pydl_block.id in all_conds:
            func = getattr(self.cond_eval, f'{cond_type}_cond')
            curr_cond = func(pydl_block, cnode)
            add_cond_expr_operands(curr_cond)
            if curr_cond is None:
                curr_cond = 1
            res = AssignValue(
                target=COND_NAME.substitute(
                    cond_type=cond_type, block_id=pydl_block.id),
                val=curr_cond)
            self._add_stmt(res)

    def _get_rst_cond(self, cnode):
        curr_cond = find_rst_cond(cnode.pydl_block)

        if curr_cond is None:
            curr_cond = 1

        if self.state_num > 0:
            rst_cond = state_expr([self.state_num], curr_cond)
        else:
            rst_cond = curr_cond
        self._add_stmt(AssignValue(target='rst_cond', val=rst_cond))

        if isinstance(curr_cond, str):
            add_cond(curr_cond)
        else:
            add_cond_expr_operands(curr_cond)

    def _get_hdl_stmt(self, cnode, pydl_block):
        if isinstance(pydl_block, Module) and self.has_registers:
            self._get_rst_cond(cnode)

        if isinstance(pydl_block, Block):
            for cond_t in self.cond_types:
                self._get_cond_by_type(cond_t, cnode, pydl_block)

    def visit_sub(self, cnode, pydl_block):
        if isinstance(pydl_block, Block):
            self._get_hdl_stmt(cnode, pydl_block)

            for stmt in pydl_block.stmts:
                self.visit_sub(cnode, stmt)

    def visit_block(self, node):
        if node.prolog:
            for block in node.prolog:
                self.visit_sub(node.parent, block)

        self._get_hdl_stmt(node, node.pydl_block)

        for child in node.child:
            self.visit(child)

        if node.epilog:
            for block in node.epilog:
                self.visit_sub(node.parent, block)

    def visit_SeqCBlock(self, node):
        return self.visit_block(node)

    def visit_MutexCBlock(self, node):
        return self.visit_block(node)

    def visit_Leaf(self, node):
        for pydl_block in node.pydl_blocks:
            self.visit_sub(node.parent, pydl_block)
