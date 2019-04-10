from . import hdl_types as ht
from .conditions import COND_NAME, find_cond_id, find_sub_cond_ids
from .hdl_stmt_types import (AssertValue, AssignValue, CombBlock,
                             CombSeparateStmts, HDLBlock)
from .hdl_utils import add_to_list, state_expr


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
    def __init__(self):
        self.control_suffix = ['_en']
        self.control_expr = (ht.IntfReadyExpr, ht.IntfValidExpr)
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
        if isinstance(name, self.control_expr):
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
                target=stmt.target, val=None, width=stmt.width)

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
    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module):
            return [AssignValue(f'{reg}_en', 0) for reg in block.data.regs]

        return None

    def visit_RegNextStmt(self, node, **kwds):
        cond = find_cycle_cond(self.conds, node, **kwds)

        return [
            AssignValue(target=f'{node.reg.name}_en', val=cond),
            AssignValue(
                target=f'{node.reg.name}_next',
                val=node.val,
                width=int(node.reg.dtype))
        ]


class VariableVisitor(HDLStmtVisitor):
    def __init__(self):
        super().__init__()
        self.seen_var = []

    def assign_var(self, name, value):
        if name not in self.seen_var:
            self.non_control_pairs.append((name, value))
            self.seen_var.append(name)

    def visit_VariableStmt(self, node, **kwds):
        name = f'{node.variable.name}_v'
        self.assign_var(name, node.val)
        return AssignValue(
            target=name, val=node.val, width=int(node.variable.dtype))


class OutputVisitor(HDLStmtVisitor):
    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module):
            self.out_ports = {p.name: p for p in block.data.out_ports}
            self.out_intfs = block.data.out_intfs
            res = []
            for port in block.data.out_ports:
                res.append(AssignValue(ht.IntfValidExpr(port), 0))

            return res

        return None

    def visit_Yield(self, node, **kwds):
        if not isinstance(node.expr, list):
            exprs = [node.expr]
        else:
            exprs = node.expr

        stmts = []
        assert len(exprs) == len(self.out_ports)

        for expr, port in zip(exprs, self.out_ports):
            if self.out_ports[port].context:
                valid = self.out_ports[port].context
            elif isinstance(expr, ht.ResExpr) and expr.val is None:
                valid = 0
            else:
                valid = 1
            stmts.append(AssignValue(ht.IntfValidExpr(port), valid))
            if (not self.out_intfs) and (valid != 0):
                stmts.append(AssignValue(f'{port}_s', expr))
        block = HDLBlock(in_cond=None, stmts=stmts, dflts={})
        self.update_defaults(block)
        return block

    def visit_IntfStmt(self, node, **kwds):
        if node.intf.name not in self.out_intfs:
            return None

        res = []
        for intf in node.intf.intf:
            res.append(
                AssignValue(
                    target=f'{intf.name}_s',
                    val=node.val,
                    width=int(node.val.dtype)))
        return res


class InputVisitor(HDLStmtVisitor):
    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module):
            self.input_names = [port.name for port in block.data.in_ports]
            return [
                AssignValue(ht.IntfReadyExpr(port), 0)
                for port in block.data.in_ports
            ]

        if isinstance(block, ht.IntfBlock):
            if block.intf.name in self.input_names:
                cond = find_exit_cond(self.conds, block, **kwds)
                return AssignValue(
                    target=ht.IntfReadyExpr(block.intf), val=cond)

        if isinstance(block, ht.IntfLoop):
            if block.intf.name in self.input_names:
                cond = find_cycle_cond(self.conds, block, **kwds)
                return AssignValue(
                    target=ht.IntfReadyExpr(block.intf), val=cond)

        return None

    def visit_IntfStmt(self, node, **kwds):
        if hasattr(node.val, 'name') and (node.val.name in self.input_names):
            return AssignValue(
                target=ht.IntfReadyExpr(node.val),
                val=ht.IntfReadyExpr(node.intf))

        return None


class IntfReadyVisitor(HDLStmtVisitor):
    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module):
            self.intf_names = block.data.in_intfs.keys()
            dflt_ready = []
            for port in block.data.in_intfs:
                dflt_ready.append(AssignValue(ht.IntfReadyExpr(port), 0))
            return dflt_ready

        if isinstance(block, ht.IntfBlock):
            if block.intf.name in self.intf_names:
                cond = find_exit_cond(self.conds, block, **kwds)
                return AssignValue(
                    target=ht.IntfReadyExpr(block.intf), val=cond)

        if isinstance(block, ht.IntfLoop):
            if block.intf.name in self.intf_names:
                cond = find_cycle_cond(self.conds, block, **kwds)
                return AssignValue(
                    target=ht.IntfReadyExpr(block.intf), val=cond)

        return None

    def visit_IntfStmt(self, node, **kwds):
        if hasattr(node.val, 'name') and (node.val.name in self.intf_names):
            return AssignValue(
                target=ht.IntfReadyExpr(node.val),
                val=ht.IntfReadyExpr(node.intf))

        return None


class IntfValidVisitor(HDLStmtVisitor):
    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module):
            self.intf_names = block.data.in_intfs.keys()
            dflt_ready = []
            for port in block.data.in_intfs:
                dflt_ready.append(AssignValue(ht.IntfValidExpr(port), 0))
            return dflt_ready

        return None

    def visit_IntfStmt(self, node, **kwds):
        if node.intf.name in self.intf_names:
            return [
                AssignValue(
                    target=f'{node.intf.name}_s',
                    val=node.val,
                    width=int(node.dtype)),
                AssignValue(
                    target=ht.IntfValidExpr(node.intf),
                    val=ht.IntfValidExpr(node.val))
            ]

        return None


class BlockConditionsVisitor(HDLStmtVisitor):
    def __init__(self, reg_num, state_num):
        super().__init__()
        self.reg_num = reg_num
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

    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module) and self.reg_num > 0:
            self.get_rst_cond(**kwds)

        for cond_t in self.cond_types:
            self.get_cond_by_type(cond_t, **kwds)


class StateTransitionVisitor(HDLStmtVisitor):
    def enter_block(self, block, **kwds):
        super().enter_block(block, **kwds)
        if isinstance(block, ht.Module):
            return AssignValue(f'state_en', 0)

        return None

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
