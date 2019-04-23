from .conditions import Conditions
from .conditions_evaluate import ConditionsEval
from .conditions_utils import COND_NAME, find_cond_id, find_sub_cond_ids
from .hdl_stmt_types import AssignValue, CombSeparateStmts
from .hls_blocks import Block, Module
from .inst_visit import InstanceVisitor
from .utils import state_expr


class AssignConditions(InstanceVisitor):
    def __init__(self, module_data, state_num):
        self.state_num = state_num
        self.cond_eval = ConditionsEval()
        self.has_registers = len(module_data.regs) > 0
        self.condition_assigns = CombSeparateStmts(stmts=[])
        self.cond_types = ['in', 'cycle', 'exit']

        # TODO : remove after refactor
        self.conds = Conditions()

    def conditions(self):
        self.get_combined()
        return self.condition_assigns

    def _add_stmt(self, stmt):
        if stmt not in self.condition_assigns.stmts:
            self.condition_assigns.stmts.append(stmt)

    def get_combined(self):
        for name, val in self.conds.combined_conds.items():
            self._add_stmt(AssignValue(target=name, val=val))

    def find_subconds(self, curr_cond):
        if curr_cond is not None and not isinstance(curr_cond, str):
            res = find_sub_cond_ids(curr_cond)
            for cond_t in self.cond_types:
                if cond_t in res:
                    for sub_id in res[cond_t]:
                        self.conds.add_cond(sub_id, cond_t)

    def get_cond_by_type(self, cond_type, cnode, hdl_block):
        all_conds = getattr(self.conds, f'{cond_type}_conds')
        if hdl_block.id in all_conds:
            func = getattr(self.cond_eval, f'{cond_type}_cond')
            curr_cond = func(hdl_block, cnode)
            self.find_subconds(curr_cond)
            if curr_cond is None:
                curr_cond = 1
            res = AssignValue(
                target=COND_NAME.substitute(
                    cond_type=cond_type, block_id=hdl_block.id),
                val=curr_cond)
            self._add_stmt(res)

    def get_rst_cond(self, cnode):
        # TODO : clean after condition refactored
        self.conds.scope = [cnode]
        self.conds.cond_finder.scope = [cnode]
        curr_cond = self.conds.find_rst_cond()

        if curr_cond is None:
            curr_cond = 1

        if self.state_num > 0:
            rst_cond = state_expr([self.state_num], curr_cond)
        else:
            rst_cond = curr_cond
        self._add_stmt(AssignValue(target='rst_cond', val=rst_cond))

        if isinstance(curr_cond, str):
            self.conds.add_exit_cond(find_cond_id(curr_cond))
        else:
            self.find_subconds(curr_cond)

    def get_hdl_stmt(self, cnode, block):
        if isinstance(block, Module) and self.has_registers:
            self.get_rst_cond(cnode)

        if isinstance(block, Block):
            for cond_t in self.cond_types:
                self.get_cond_by_type(cond_t, cnode, block)

    def visit_sub(self, cnode, hdl_block):
        if isinstance(hdl_block, Block):
            self.get_hdl_stmt(cnode, hdl_block)

            for stmt in hdl_block.stmts:
                self.visit_sub(cnode, stmt)

    def visit_block(self, node):
        if node.prolog:
            for block in node.prolog:
                self.visit_sub(node.parent, block)

        self.get_hdl_stmt(node, node.hdl_block)

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
        for hdl_block in node.hdl_blocks:
            self.visit_sub(node.parent, hdl_block)
