import hdl_types as ht

from .hdl_stmt_types import AssignValue, CombBlock, CombSeparateStmts, HDLBlock
from .hdl_utils import add_to_list, state_expr


def find_cond(cond, **kwds):
    if cond is None:
        cond = 1
    if 'context_cond' in kwds:
        cond = ht.and_expr(cond, kwds['context_cond'])
    return cond


def find_cycle_cond(conds, **kwds):
    return find_cond(cond=conds.cycle_cond, **kwds)


def find_rst_cond(conds, **kwds):
    return find_cond(cond=conds.rst_cond, **kwds)


def find_exit_cond(conds, **kwds):
    return find_cond(cond=conds.exit_cond, **kwds)


class HDLStmtVisitor:
    def __init__(self):
        self.control_suffix = ['_en', '.valid', '.ready']
        self.current_scope = None

    def visit(self, node, conds, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, ht.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, ht.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        return visitor(node, conds, **kwds)

    def generic_visit(self, node, conds, **kwds):
        pass

    def enter_block(self, block, conds, **kwds):
        self.current_scope = block

    def visit_Module(self, node, conds, **kwds):
        block = CombBlock(stmts=[], dflts={})
        return self.traverse_block(block, node, conds, **kwds)

    def visit_all_Block(self, node, conds, **kwds):
        block = HDLBlock(in_cond=node.in_cond, stmts=[], dflts={})
        return self.traverse_block(block, node, conds, **kwds)

    def traverse_block(self, block, node, conds, **kwds):
        add_to_list(block.stmts, self.enter_block(node, conds, **kwds))

        # if block isn't empty
        if block.stmts:
            self.update_defaults(block)

        return block

    def is_control_var(self, name):
        for suff in self.control_suffix:
            if name.endswith(suff):
                return True
        return False

    def find_stmt_dflt(self, stmt, block):
        for dflt in stmt.dflts:
            # control cannot propagate past in conditions
            if (not self.is_control_var(dflt)) or not stmt.in_cond:
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
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            return [AssignValue(f'{reg}_en', 0) for reg in block.regs]

        return None

    def visit_RegNextStmt(self, node, conds, **kwds):
        cond = find_cycle_cond(conds=conds, **kwds)

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

    def assign_var(self, name):
        if name in self.seen_var:
            if name not in self.control_suffix:
                self.control_suffix.append(name)
        else:
            self.seen_var.append(name)

    def visit_VariableStmt(self, node, conds, **kwds):
        name = f'{node.variable.name}_v'
        self.assign_var(name)
        return AssignValue(
            target=name, val=node.val, width=int(node.variable.dtype))


class OutputVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            self.out_ports = {p.name: p for p in block.out_ports}
            self.out_intfs = block.out_intfs
            res = []
            for port in block.out_ports:
                res.append(AssignValue(f'{port.name}.valid', 0))

            return res

        return None

    def visit_Yield(self, node, conds, **kwds):
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
            stmts.append(AssignValue(f'{port}.valid', valid))
            if (not self.out_intfs) and (valid != 0):
                stmts.append(AssignValue(f'{port}_s', expr))
        block = HDLBlock(in_cond=None, stmts=stmts, dflts={})
        self.update_defaults(block)
        return block

    def visit_IntfStmt(self, node, conds, **kwds):
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
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            self.input_names = [port.name for port in block.in_ports]
            return [
                AssignValue(f'{port.name}.ready', 0) for port in block.in_ports
            ]

        if isinstance(block, ht.IntfBlock):
            if block.intf.name in self.input_names:
                cond = find_exit_cond(conds=conds, **kwds)
                return AssignValue(target=f'{block.intf.name}.ready', val=cond)

        if isinstance(block, ht.IntfLoop):
            if block.intf.name in self.input_names:
                cond = find_cycle_cond(conds=conds, **kwds)
                return AssignValue(target=f'{block.intf.name}.ready', val=cond)

        return None

    def visit_IntfStmt(self, node, conds, **kwds):
        if hasattr(node.val, 'name') and (node.val.name in self.input_names):
            return AssignValue(
                target=f'{node.val.name}.ready', val=f'{node.intf.name}.ready')

        return None


class IntfReadyVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            self.intf_names = block.intfs.keys()
            dflt_ready = []
            for port in block.intfs:
                dflt_ready.append(AssignValue(f'{port}.ready', 0))
            return dflt_ready

        if isinstance(block, ht.IntfBlock):
            if block.intf.name in self.intf_names:
                cond = find_exit_cond(conds=conds, **kwds)
                return AssignValue(target=f'{block.intf.name}.ready', val=cond)

        if isinstance(block, ht.IntfLoop):
            if block.intf.name in self.intf_names:
                cond = find_cycle_cond(conds=conds, **kwds)
                return AssignValue(target=f'{block.intf.name}.ready', val=cond)

        return None

    def visit_IntfStmt(self, node, conds, **kwds):
        if hasattr(node.val, 'name') and (node.val.name in self.intf_names):
            return AssignValue(
                target=f'{node.val.name}.ready', val=f'{node.intf.name}.ready')

        return None


class IntfValidVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            self.intf_names = block.intfs.keys()
            dflt_ready = []
            for port in block.intfs:
                dflt_ready.append(AssignValue(f'{port}.valid', 0))
            return dflt_ready

        return None

    def visit_IntfStmt(self, node, conds, **kwds):
        if node.intf.name in self.intf_names:
            return [
                AssignValue(
                    target=f'{node.intf.name}_s',
                    val=node.val,
                    width=int(node.dtype)),
                AssignValue(
                    target=f'{node.intf.name}.valid',
                    val=f'{node.val.name}.valid')
            ]

        return None


class BlockConditionsVisitor(HDLStmtVisitor):
    def __init__(self, cycle_conds, exit_conds, reg_num, state_num):
        super().__init__()
        self.cycle_conds = cycle_conds
        self.exit_conds = exit_conds
        self.reg_num = reg_num
        self.state_num = state_num
        self.in_conds = []
        self.condition_assigns = CombSeparateStmts(stmts=[])

    def find_subconds(self, cond):
        if cond is not None and not isinstance(cond, str):
            res = ht.find_sub_cond_ids(cond)
            if 'exit' in res:
                for sub_id in res['exit']:
                    if sub_id not in self.exit_conds:
                        self.exit_conds.append(sub_id)
            if 'cycle' in res:
                for sub_id in res['cycle']:
                    if sub_id not in self.cycle_conds:
                        self.cycle_conds.append(sub_id)
            if 'in' in res:
                for sub_id in res['in']:
                    if sub_id not in self.in_conds:
                        self.in_conds.append(sub_id)

    def get_cycle_cond(self):
        if self.current_scope.id in self.cycle_conds:
            cond = self.current_scope.cycle_cond
            self.find_subconds(cond)
            if cond is None:
                cond = 1
            res = AssignValue(
                target=ht.COND_NAME.substitute(
                    cond_type='cycle', block_id=self.current_scope.id),
                val=cond)
            if res not in self.condition_assigns.stmts:
                self.condition_assigns.stmts.append(res)

    def get_exit_cond(self):
        if self.current_scope.id in self.exit_conds:
            cond = self.current_scope.exit_cond
            self.find_subconds(cond)
            if cond is None:
                cond = 1
            res = AssignValue(
                target=ht.COND_NAME.substitute(
                    cond_type='exit', block_id=self.current_scope.id),
                val=cond)
            if res not in self.condition_assigns.stmts:
                self.condition_assigns.stmts.append(res)

    def get_in_cond(self):
        if self.current_scope.id in self.in_conds:
            cond = self.current_scope.in_cond
            if cond is None:
                cond = 1
            res = AssignValue(
                target=ht.COND_NAME.substitute(
                    cond_type='in', block_id=self.current_scope.id),
                val=cond)
            if res not in self.condition_assigns.stmts:
                self.condition_assigns.stmts.append(res)

    def get_rst_cond(self, conds, **kwds):
        cond = find_rst_cond(conds, **kwds)
        if cond is None:
            cond = 1

        if self.state_num > 0:
            rst_cond = state_expr([self.state_num], cond)
        else:
            rst_cond = cond
        res = AssignValue(target='rst_cond', val=rst_cond)
        self.condition_assigns.stmts.append(res)

        if isinstance(cond, str):
            self.exit_conds.append(ht.find_cond_id(cond))
        else:
            self.find_subconds(cond)

    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module) and self.reg_num > 0:
            self.get_rst_cond(conds, **kwds)
        self.get_cycle_cond()
        self.get_exit_cond()
        self.get_in_cond()  # must be last


class StateTransitionVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            return AssignValue(f'state_en', 0)

        return None

    def visit_all_Block(self, node, conds, **kwds):
        block = super().visit_all_Block(node, conds, **kwds)

        if 'state_id' in kwds:
            cond = find_exit_cond(conds=conds, **kwds)
            add_to_list(block.stmts, [
                AssignValue(target=f'state_en', val=cond),
                AssignValue(target='state_next', val=kwds['state_id'])
            ])
            if block.stmts:
                self.update_defaults(block)

        return block
