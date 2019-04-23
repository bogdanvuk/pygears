from .hdl_stmt_types import (AssertValue, AssignValue, CombBlock,
                             CombSeparateStmts, HDLBlock)
from .hls_blocks import Block
from .hls_expressions import (Expr, IntfReadyExpr, IntfValidExpr, OperandVal,
                              RegDef, ResExpr, SubscriptExpr, VariableDef)
from .utils import VisitError, add_to_list


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

        if visitor.__name__ == 'generic_visit' and isinstance(node, Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, Expr):
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
        if isinstance(name, Expr):
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

    if isinstance(node_var, (RegDef, VariableDef)):
        next_target = f'{node.name}_{context}'
    elif isinstance(node_var, SubscriptExpr):
        sub_val = node_var.val
        next_target = SubscriptExpr(
            val=OperandVal(op=sub_val.op, context=context),
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
            AssignValue(IntfValidExpr(port), 0)
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
            elif isinstance(expr, ResExpr) and expr.val is None:
                valid = 0
            else:
                valid = 1
            stmts.append(AssignValue(IntfValidExpr(port_name), valid))
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
            AssignValue(IntfReadyExpr(port), 0)
            for port in self.input_target.values()
        ]

    def enter_IntfBlock(self, block, **kwds):
        if block.intf.name in self.input_target:
            cond = find_exit_cond(self.conds, block, **kwds)
            return AssignValue(target=IntfReadyExpr(block.intf), val=cond)

    def enter_IntfLoop(self, block, **kwds):
        if block.intf.name in self.input_target:
            cond = find_cycle_cond(self.conds, block, **kwds)
            return AssignValue(target=IntfReadyExpr(block.intf), val=cond)

    def visit_IntfStmt(self, node, **kwds):
        if hasattr(node.val, 'name') and (node.val.name in self.input_target):
            return AssignValue(
                target=IntfReadyExpr(node.val), val=IntfReadyExpr(node.intf))


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
            AssignValue(IntfReadyExpr(port), 0)
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
                    target=IntfValidExpr(node.intf),
                    val=IntfValidExpr(node.val))
            ]

        return None


class AssertionVisitor(HDLStmtVisitor):
    def visit_AssertExpr(self, node, **kwds):
        return AssertValue(node)
