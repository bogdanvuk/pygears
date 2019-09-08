from functools import partial

from .conditions_utils import COND_NAME, add_found_cond
from .hdl_types import AssertValue, AssignValue, CombBlock, HDLBlock, FuncBlock, FuncReturn
from .hls_expressions import (ConcatExpr, Expr, IntfReadyExpr, IntfValidExpr,
                              OperandVal, RegDef, ResExpr, SubscriptExpr,
                              VariableDef, ConditionalExpr, SignalDef)
from .pydl_types import Block
from .utils import VisitError, add_to_list

CONTROL_SUFFIX = ['_en']


def find_cond(block, ctype):
    curr_cond = getattr(block.cond_val, f'{ctype}_val')

    if curr_cond is not None:
        add_found_cond(block.cond_val.name, ctype)
        return COND_NAME.substitute(cond_type=ctype,
                                    block_id=block.cond_val.name)

    if ctype == 'in':  # avoid unnecessary if(1) blocks
        return None
    return 1


def is_control_var(name, val, non_control_pairs=None):
    if isinstance(name, Expr):
        return True

    for suff in CONTROL_SUFFIX:
        if name.endswith(suff):
            return True

    if non_control_pairs is not None:
        if isinstance(val, AssignValue):
            val = val.val
        for ctrl_name, ctrl_val in non_control_pairs:
            if name == ctrl_name:
                if val != ctrl_val:
                    return True

    return False


def find_stmt_dflt(stmt, block, non_control_pairs=None):
    for dflt in stmt.dflts:
        # control cannot propagate past in conditions
        if (not is_control_var(dflt, stmt.dflts[dflt],
                               non_control_pairs)) or not stmt.in_cond:
            if dflt in block.dflts:
                if block.dflts[dflt].val is stmt.dflts[dflt].val:
                    stmt.dflts[dflt] = None
            else:
                block.dflts[dflt] = stmt.dflts[dflt]
                stmt.dflts[dflt] = None


def find_assign_dflt(stmt, block, idx):
    if stmt.target in block.dflts:
        if block.dflts[stmt.target].val is stmt.val:
            stmt.val = None
    else:
        block.dflts[stmt.target] = stmt
        block.stmts[idx] = AssignValue(target=stmt.target,
                                       val=None,
                                       dtype=stmt.dtype)


def block_cleanup(block):
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


def update_hdl_block(block, non_control_pairs=None):
    # bottom up
    # popagate defaulf values from sub statements to top
    for i, stmt in enumerate(block.stmts):
        if hasattr(stmt, 'dflts'):
            find_stmt_dflt(stmt, block, non_control_pairs)
        elif isinstance(stmt, AssignValue):
            find_assign_dflt(stmt, block, i)

    block_cleanup(block)

    # top down
    # if there are multiple stmts with different in_conds, but same dflt
    for dflt in block.dflts:
        for stmt in block.stmts:
            if hasattr(stmt, 'dflts') and dflt in stmt.dflts:
                if block.dflts[dflt].val == stmt.dflts[dflt].val:
                    stmt.dflts[dflt] = None

    block_cleanup(block)


class HDLStmtVisitor:
    def __init__(self, hdl_data):
        self.hdl_data = hdl_data
        self.non_control_pairs = []

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

    def enter_block(self, block):
        method = 'enter_' + block.__class__.__name__
        enter_visitor = getattr(self, method, self.generic_enter)
        return enter_visitor(block)

    def generic_enter(self, block):
        pass

    def visit_Module(self, node, **kwds):
        block = CombBlock(stmts=[], dflts={})
        return self.traverse_block(block, node)

    def visit_all_Block(self, node, **kwds):
        in_cond = find_cond(node, 'in')
        block = HDLBlock(in_cond=in_cond, stmts=[], dflts={})
        return self.traverse_block(block, node)

    def traverse_block(self, block, node):
        add_to_list(block.stmts, self.enter_block(node))

        # if block isn't empty
        if block.stmts:
            self.update_defaults(block)

        return block

    def update_defaults(self, block):
        update_hdl_block(block, self.non_control_pairs)


class RegEnVisitor(HDLStmtVisitor):
    def enter_Module(self, block):
        return [AssignValue(f'{reg}_en', 0) for reg in self.hdl_data.regs]

    def visit_RegNextStmt(self, node, **kwds):
        en_cond = getattr(self.hdl_data.hdl_locals[node.name], 'en_cond', None)
        if en_cond is None:
            en_cond = find_cond(node, 'cycle')

        return [
            AssignValue(target=f'{node.name}_en', val=en_cond),
            parse_stmt_target(node, 'next')
        ]


def parse_stmt_target(node, context):
    if context in ['reg', 'next']:
        node_var = node.reg
    elif context == 'v':
        node_var = node.variable

    if isinstance(node_var, (RegDef, VariableDef)):
        next_target = f'{node.name}_{context}'
    elif isinstance(node_var, SignalDef):
        next_target = node.name
    elif isinstance(node_var, SubscriptExpr):
        sub_val = node_var.val
        next_target = SubscriptExpr(val=OperandVal(op=sub_val.op,
                                                   context=context),
                                    index=node_var.index)
    else:
        breakpoint()
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


class OutSigVisitor(HDLStmtVisitor):
    def __init__(self, hdl_data):
        super().__init__(hdl_data)
        self.seen_var = []

    def assign_var(self, name, value):
        if name not in self.seen_var:
            self.non_control_pairs.append((name, value))
            self.seen_var.append(name)

    def visit_SignalStmt(self, node, **kwds):
        self.assign_var(node.name, node.val)
        return parse_stmt_target(node, 'v')


class FunctionVisitor(HDLStmtVisitor):
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

    def visit_ReturnStmt(self, node, **kwds):
        return FuncReturn(func=self.func_block, expr=node.val)

    def visit_Function(self, node, **kwds):
        block = FuncBlock(stmts=[],
                          dflts={},
                          args=node.args,
                          name=node.name,
                          ret_dtype=node.ret_dtype)

        self.func_block = block

        return self.traverse_block(block, node)

    def traverse_block(self, block, node):
        for stmt in node.stmts:
            add_to_list(block.stmts, self.visit(stmt))

        return block

    def visit_all_Block(self, node, **kwds):
        block = HDLBlock(in_cond=node.in_cond, stmts=[], dflts={})
        return self.traverse_block(block, node)


class OutputVisitor(HDLStmtVisitor):
    def enter_Module(self, block):
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
                    AssignValue(target=f'{port_name}_s',
                                val=expr,
                                dtype=port.dtype))
        in_cond = find_cond(node, 'in')
        block = HDLBlock(in_cond=in_cond, stmts=stmts, dflts={})
        self.update_defaults(block)
        return block

    def visit_IntfStmt(self, node, **kwds):
        if node.intf.name not in self.hdl_data.out_intfs:
            return None

        res = []
        for intf in node.intf.intf:
            res.append(
                AssignValue(target=f'{intf.basename}_s',
                            val=node.val,
                            dtype=node.val.dtype))
        return res


class ReadyBase(HDLStmtVisitor):
    @property
    def input_target(self):
        raise NotImplementedError('Input target not set')

    def enter_Module(self, block):
        res = []
        for port in self.input_target.values():
            if port.has_subop:
                if isinstance(port.intf, ConcatExpr):
                    res.extend([
                        AssignValue(
                            IntfReadyExpr(op),
                            ConditionalExpr(operands=(0, "1'bx"),
                                            cond=IntfValidExpr(op)))
                        for op in port.intf.operands
                        if op.name in self.input_target
                    ])
                raise VisitError('Unsupported expression type in IntfDef')
            else:
                val = ConditionalExpr(operands=(0, "1'bx"),
                                      cond=IntfValidExpr(port))
                res.append(AssignValue(IntfReadyExpr(port), val))
        return res

    def _enter_intf(self, block, cond_func):
        if block.intf.name in self.input_target:
            val = cond_func(block)
            return AssignValue(target=IntfReadyExpr(block.intf), val=val)

        if block.intf.has_subop:
            intf_def = block.intf.intf
            if isinstance(intf_def, ConcatExpr):
                val = cond_func(block)
                return [
                    AssignValue(target=IntfReadyExpr(op), val=val)
                    for op in intf_def.operands if op.name in self.input_target
                ]
            raise VisitError('Unsupported expression type in IntfDef')

    def enter_IntfBlock(self, block):
        return self._enter_intf(block, partial(find_cond, ctype='exit'))

    def enter_IntfLoop(self, block):
        return self._enter_intf(block, partial(find_cond, ctype='cycle'))

    def visit_IntfStmt(self, node):
        if hasattr(node.val, 'name'):
            if node.val.name in self.input_target:
                return AssignValue(target=IntfReadyExpr(node.val),
                                   val=IntfReadyExpr(node.intf))

            if node.intf.has_subop:
                if isinstance(node.val, ConcatExpr):
                    return [
                        AssignValue(target=IntfReadyExpr(op),
                                    val=IntfReadyExpr(node.intf))
                        for op in node.val.operands
                        if op.name in self.input_target
                    ]
                raise VisitError('Unsupported expression type in IntfDef')


class InputVisitor(ReadyBase):
    @property
    def input_target(self):
        return self.hdl_data.in_ports


class IntfReadyVisitor(ReadyBase):
    @property
    def input_target(self):
        return self.hdl_data.in_intfs


class IntfValidVisitor(HDLStmtVisitor):
    def enter_Module(self, block):
        return [
            AssignValue(IntfValidExpr(port), 0)
            for port in self.hdl_data.in_intfs
        ]

    def visit_IntfStmt(self, node, **kwds):
        if node.intf.name in self.hdl_data.in_intfs:
            return [
                AssignValue(target=f'{node.intf.name}_s',
                            val=node.val,
                            dtype=node.dtype),
                AssignValue(target=IntfValidExpr(node.intf),
                            val=IntfValidExpr(node.val))
            ]

        return None


class AssertionVisitor(HDLStmtVisitor):
    def visit_AssertExpr(self, node, **kwds):
        return AssertValue(node)
