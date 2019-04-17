from . import hdl_types as ht
from .conditions_utils import COND_NAME, find_cond_id, find_sub_cond_ids
from .hdl_stmt_types import (AssertValue, AssignValue, CombBlock,
                             CombSeparateStmts, HDLBlock)
from .hdl_utils import VisitError, add_to_list, state_expr


def find_in_cond(conds, hdl_stmt, **kwds):
    if len(str(hdl_stmt.in_cond)) > 150:  # major hack for code readability
        return conds.find_in_cond(hdl_stmt, **kwds)

    if hdl_stmt.in_cond is not None:
        conds.add_in_cond(hdl_stmt.id)
    return hdl_stmt.in_cond


def find_cycle_cond(conds, hdl_stmt, **kwds):
    return conds.find_cycle_cond(hdl_stmt, **kwds)


def find_rst_cond(conds, **kwds):
    return conds.find_rst_cond(**kwds)


def find_exit_cond(conds, hdl_stmt, **kwds):
    return conds.find_exit_cond(hdl_stmt, **kwds)


class HDLStmtVisitor:
    def __init__(self, hdl_data):
        self.hdl_data = hdl_data
        self.control_suffix = ['_en']
        self.non_control_pairs = []
        self.current_scope = None
        self.conds = None

    def visit(self, node, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, ht.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, ht.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        return visitor(node, **kwds)

    def generic_visit(self, node, **kwds):
        pass

    def enter_block(self, block, **kwds):
        self.current_scope = block
        method = 'enter_' + block.__class__.__name__
        enter_visitor = getattr(self, method, self.generic_enter)
        return enter_visitor(block, **kwds)

    def generic_enter(self, block, **kwds):
        pass

    def visit_Module(self, node, **kwds):
        block = CombBlock(stmts=[], dflts={})
        return self.traverse_block(block, node, **kwds)

    def visit_all_Block(self, node, **kwds):
        in_cond = find_in_cond(self.conds, node, **kwds)
        block = HDLBlock(in_cond=in_cond, stmts=[], dflts={})
        return self.traverse_block(block, node, **kwds)

    def traverse_block(self, block, node, **kwds):
        add_to_list(block.stmts, self.enter_block(node, **kwds))

        # if block isn't empty
        if block.stmts:
            self.update_defaults(block)

        return block

    def is_control_var(self, name, val):
        if isinstance(name, ht.Expr):
            return True

        for suff in self.control_suffix:
            if name.endswith(suff):
                return True

        if isinstance(val, AssignValue):
            val = val.val
        for ctrl_name, ctrl_val in self.non_control_pairs:
            if name == ctrl_name:
                if val != ctrl_val:
                    return True

        return False

    def find_stmt_dflt(self, stmt, block):
        for dflt in stmt.dflts:
            # control cannot propagate past in conditions
            if (not self.is_control_var(dflt,
                                        stmt.dflts[dflt])) or not stmt.in_cond:
                if dflt in block.dflts:
                    if block.dflts[dflt].val is stmt.dflts[dflt].val:
                        stmt.dflts[dflt] = None
                else:
                    block.dflts[dflt] = stmt.dflts[dflt]
                    stmt.dflts[dflt] = None

    def find_assign_dflt(self, stmt, block, idx):
        if stmt.target in block.dflts:
            if block.dflts[stmt.target].val is stmt.val:
                stmt.val = None
        else:
            block.dflts[stmt.target] = stmt
            block.stmts[idx] = AssignValue(
                target=stmt.target, val=None, dtype=stmt.dtype)

    def update_defaults(self, block):
        # bottom up
        # popagate defaulf values from sub statements to top
        for i, stmt in enumerate(block.stmts):
            if hasattr(stmt, 'dflts'):
                self.find_stmt_dflt(stmt, block)
            elif isinstance(stmt, AssignValue):
                self.find_assign_dflt(stmt, block, i)

        self.block_cleanup(block)

        # top down
        # if there are multiple stmts with different in_conds, but same dflt
        for dflt in block.dflts:
            for stmt in block.stmts:
                if hasattr(stmt, 'dflts') and dflt in stmt.dflts:
                    if block.dflts[dflt].val == stmt.dflts[dflt].val:
                        stmt.dflts[dflt] = None

        self.block_cleanup(block)

    def block_cleanup(self, block):
        # cleanup None statements
        for i, stmt in reversed(list(enumerate(block.stmts))):
            if hasattr(stmt, 'val') and stmt.val is None:
                del block.stmts[i]
            if hasattr(stmt, 'dflts'):
                for name in list(stmt.dflts.keys()):
                    if stmt.dflts[name] is None:
                        del stmt.dflts[name]
                if (not stmt.dflts) and (not stmt.stmts):
                    del block.stmts[i]


class RegEnVisitor(HDLStmtVisitor):
    def enter_Module(self, block, **kwds):
        return [AssignValue(f'{reg}_en', 0) for reg in self.hdl_data.regs]

    def visit_RegNextStmt(self, node, **kwds):
        cond = find_cycle_cond(self.conds, node, **kwds)

        return [
            AssignValue(target=f'{node.name}_en', val=cond),
            parse_stmt_target(node, 'next')
        ]


def parse_stmt_target(node, context):
    if context in ['reg', 'next']:
        node_var = node.reg
    elif context == 'v':
        node_var = node.variable

    if isinstance(node_var, (ht.RegDef, ht.VariableDef)):
        next_target = f'{node.name}_{context}'
    elif isinstance(node_var, ht.SubscriptExpr):
        sub_val = node_var.val
        next_target = ht.SubscriptExpr(
            val=ht.OperandVal(op=sub_val.op, context=context),
            index=node_var.index)
    else:
        raise VisitError('Unknown assignment type')

    return AssignValue(target=next_target, val=node.val, dtype=node_var.dtype)


class VariableVisitor(HDLStmtVisitor):
    def __init__(self, hdl_data):
        super().__init__(hdl_data)
        self.seen_var = []

    def assign_var(self, name, value):
        if name not in self.seen_var:
            self.non_control_pairs.append((name, value))
            self.seen_var.append(name)

    def visit_VariableStmt(self, node, **kwds):
        self.assign_var(f'{node.name}_v', node.val)
        return parse_stmt_target(node, 'v')


class OutputVisitor(HDLStmtVisitor):
    def enter_Module(self, block, **kwds):
        return [
            AssignValue(ht.IntfValidExpr(port), 0)
            for port in self.hdl_data.out_ports.values()
        ]

    def visit_Yield(self, node, **kwds):
        if not isinstance(node.expr, list):
            exprs = [node.expr]
        else:
            exprs = node.expr

        stmts = []
        assert len(exprs) == len(self.hdl_data.out_ports)

        for expr, (port_name, port) in zip(exprs,
                                           self.hdl_data.out_ports.items()):
            if port.context:
                valid = port.context
            elif isinstance(expr, ht.ResExpr) and expr.val is None:
                valid = 0
            else:
                valid = 1
            stmts.append(AssignValue(ht.IntfValidExpr(port_name), valid))
            if (not self.hdl_data.out_intfs) and (valid != 0):
                stmts.append(
                    AssignValue(
                        target=f'{port_name}_s', val=expr, dtype=port.dtype))
        block = HDLBlock(in_cond=None, stmts=stmts, dflts={})
        self.update_defaults(block)
        return block

    def visit_IntfStmt(self, node, **kwds):
        if node.intf.name not in self.hdl_data.out_intfs:
            return None

        res = []
        for intf in node.intf.intf:
            res.append(
                AssignValue(
                    target=f'{intf.basename}_s',
                    val=node.val,
                    dtype=node.val.dtype))
        return res


class ReadyBase(HDLStmtVisitor):
    @property
    def input_target(self):
        raise NotImplementedError('Input target not set')

    def enter_Module(self, block, **kwds):
        return [
            AssignValue(ht.IntfReadyExpr(port), 0)
            for port in self.input_target.values()
        ]

    def enter_IntfBlock(self, block, **kwds):
        if block.intf.name in self.input_target:
            cond = find_exit_cond(self.conds, block, **kwds)
            return AssignValue(target=ht.IntfReadyExpr(block.intf), val=cond)

    def enter_IntfLoop(self, block, **kwds):
        if block.intf.name in self.input_target:
            cond = find_cycle_cond(self.conds, block, **kwds)
            return AssignValue(target=ht.IntfReadyExpr(block.intf), val=cond)

    def visit_IntfStmt(self, node, **kwds):
        if hasattr(node.val, 'name') and (node.val.name in self.input_target):
            return AssignValue(
                target=ht.IntfReadyExpr(node.val),
                val=ht.IntfReadyExpr(node.intf))


class InputVisitor(ReadyBase):
    @property
    def input_target(self):
        return self.hdl_data.in_ports


class IntfReadyVisitor(ReadyBase):
    @property
    def input_target(self):
        return self.hdl_data.in_intfs


class IntfValidVisitor(HDLStmtVisitor):
    def enter_Module(self, block, **kwds):
        return [
            AssignValue(ht.IntfReadyExpr(port), 0)
            for port in self.hdl_data.in_intfs
        ]

    def visit_IntfStmt(self, node, **kwds):
        if node.intf.name in self.hdl_data.in_intfs:
            return [
                AssignValue(
                    target=f'{node.intf.name}_s',
                    val=node.val,
                    dtype=node.dtype),
                AssignValue(
                    target=ht.IntfValidExpr(node.intf),
                    val=ht.IntfValidExpr(node.val))
            ]

        return None


class BlockConditionsVisitor(HDLStmtVisitor):
    def __init__(self, hdl_data, state_num):
        super().__init__(hdl_data)
        self.has_registers = len(hdl_data.regs) > 0
        self.state_num = state_num
        self.condition_assigns = CombSeparateStmts(stmts=[])
        self.cond_types = ['in', 'cycle', 'exit']

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

    def get_cond_by_type(self, cond_type, **kwds):
        all_conds = getattr(self.conds, f'{cond_type}_conds')
        if self.current_scope.id in all_conds:
            curr_cond = self.conds.eval_cond(self.current_scope, cond_type)
            self.find_subconds(curr_cond)
            if curr_cond is None:
                curr_cond = 1
            res = AssignValue(
                target=COND_NAME.substitute(
                    cond_type=cond_type, block_id=self.current_scope.id),
                val=curr_cond)
            self._add_stmt(res)

    def get_rst_cond(self, **kwds):
        curr_cond = find_rst_cond(self.conds, **kwds)
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

    def generic_enter(self, block, **kwds):
        if isinstance(block, ht.Module) and self.has_registers:
            self.get_rst_cond(**kwds)

        for cond_t in self.cond_types:
            self.get_cond_by_type(cond_t, **kwds)


class StateTransitionVisitor(HDLStmtVisitor):
    def enter_Module(self, block, **kwds):
        return AssignValue(f'state_en', 0)

    def visit_all_Block(self, node, **kwds):
        block = super().visit_all_Block(node, **kwds)
        if 'state_id' not in kwds:
            return block

        return self.assign_states(block, **kwds)

    def assign_states(self, block, **kwds):
        state_tr = kwds['state_id']

        cond = self.conds.find_exit_cond_by_scope(state_tr.scope)
        if cond is None:
            cond = 1

        add_to_list(
            block.stmts,
            HDLBlock(
                in_cond=cond,
                stmts=[AssignValue(target=f'state_en', val=1)],
                dflts={
                    'state_next':
                    AssignValue(target='state_next', val=state_tr.next_state)
                }))

        if block.stmts:
            self.update_defaults(block)

        return block


class AssertionVisitor(HDLStmtVisitor):
    def visit_AssertExpr(self, node, **kwds):
        return AssertValue(node)
