from .conditions_utils import COND_NAME, COND_TYPES, UsedConditions
from .hdl_types import AssignValue, CombSeparateStmts
from .inst_visit import PydlFromCBlockVisitor
from .pydl_types import Module


class AssignConditions(PydlFromCBlockVisitor):
    def __init__(self, module_data, state_num):
        self.state_num = state_num
        self.has_registers = len(module_data.regs) > 0
        self.condition_assigns = CombSeparateStmts(stmts=[])

    def get_condition_block(self):
        return self.condition_assigns

    def _add_stmt(self, stmt):
        if stmt not in self.condition_assigns.stmts:
            self.condition_assigns.stmts.append(stmt)

    def _get_cond_by_type(self, cond_type, node):
        all_conds = getattr(UsedConditions, f'{cond_type}_conds')
        if node.cond_val.name in all_conds:
            curr_cond = getattr(node.cond_val, f'{cond_type}_val')
            if curr_cond is None:
                curr_cond = 1
            res = AssignValue(
                target=COND_NAME.substitute(
                    cond_type=cond_type, block_id=node.cond_val.name),
                val=curr_cond)
            self._add_stmt(res)

    def visit_all_Block(self, node):
        if isinstance(node, Module) and self.has_registers:
            self._add_stmt(
                AssignValue(target='rst_cond', val=node.cond_val.exit_val))

        for cond_t in COND_TYPES:
            self._get_cond_by_type(cond_t, node)

    def visit_all_Expr(self, node):
        for cond_t in COND_TYPES:
            self._get_cond_by_type(cond_t, node)
