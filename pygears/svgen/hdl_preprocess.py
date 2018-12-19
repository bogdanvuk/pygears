import typing as pytypes

import hdl_types as ht
from pygears.typing import Array, Integer, typeof, Queue
from pygears.typing.base import TypingMeta


class AssignValue(pytypes.NamedTuple):
    target: pytypes.Any
    val: pytypes.Any
    width: TypingMeta = None


class CombBlock(pytypes.NamedTuple):
    stmts: pytypes.List
    dflts: pytypes.Dict


class SVBlock(pytypes.NamedTuple):
    stmts: pytypes.List
    dflts: pytypes.Dict
    in_cond: str = None
    else_cond: str = None


class InstanceVisitor:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        import pdb
        pdb.set_trace()
        raise Exception


def svexpr(expr):
    v = SVExpressionVisitor()
    return v.visit(expr)


class SVExpressionVisitor(InstanceVisitor):
    def visit_VariableVal(self, node):
        return node.name

    def visit_RegVal(self, node):
        return node.name

    def visit_ResExpr(self, node):
        return int(node.val)

    def visit_IntfReadyExpr(self, node):
        return 'dout.ready'

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        if typeof(node.val.dtype, Queue):
            try:
                node.val.dtype[node.attr[0]]
            except KeyError:
                val.append('data')
        return '.'.join(val + node.attr)

    def visit_ConcatExpr(self, node):
        return (
            '{' + ', '.join(self.visit(op)
                            for op in reversed(node.operands)) + '}')

    def visit_ArrayOpExpr(self, node):
        val = self.visit(node.array)
        return f'{node.operator}({val})'

    def visit_UnaryOpExpr(self, node):
        val = self.visit(node.operand)
        return f'{node.operator}({val})'

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        for i, op in enumerate(node.operands):
            if isinstance(op, ht.BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator in ht.extendable_operators:
            svrepr = (f"{int(node.dtype)}'({ops[0]})"
                      f" {node.operator} "
                      f"{int(node.dtype)}'({ops[1]})")
        else:
            svrepr = f'{ops[0]} {node.operator} {ops[1]}'
        return svrepr

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        if isinstance(node.index, slice):
            return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'
        else:
            if typeof(node.val.dtype, Array) or typeof(node.val.dtype,
                                                       Integer):
                return f'{val}[{node.index}]'
            else:
                return f'{val}.{node.val.dtype.fields[node.index]}'

    def visit_IntfExpr(self, node):
        if node.context:
            if node.context is 'eot':
                return f'&{node.intf.basename}_s.{node.context}'
            else:
                return f'{node.intf.basename}.{node.context}'
        else:
            return f'{node.intf.basename}_s'


class SVCompilerPreprocess(InstanceVisitor):
    def __init__(self):
        self.svlines = []
        self.scope = []
        self.stages = []

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    @property
    def current_stage(self):
        return self.stages[-1]

    def generic_visit(self, node):
        pass

    def visit_Module(self, node):
        self.module = node
        comb_block = CombBlock(stmts=[], dflts={})
        self.stages.append(node)
        self.traverse_block(comb_block, node)

        # if not comb_block.stmts and not comb_block.dflts:
        #     # variable isn't always assigned
        #     # it can be implicit in a loop
        #     if self.visit_var in node.variables:
        #         var = node.variables[self.visit_var]
        #         value = svexpr(var.variable.val)
        #         name = f'{self.visit_var}_v'
        #         comb_block.dflts[name] = AssignValue(name, value,
        #                                              int(var.dtype))

        return comb_block

    def visit_IfBlock(self, node):
        in_cond = svexpr(node.in_cond)
        svblock = SVBlock(in_cond=in_cond, stmts=[], dflts={})
        return self.traverse_block(svblock, node)

    def visit_IntfBlock(self, node):
        svblock = SVBlock(in_cond=svexpr(node.in_cond), stmts=[], dflts={})
        return self.traverse_block(svblock, node)

    def visit_IntfLoop(self, node):
        return self.visit_IntfBlock(node)

    def visit_Stage(self, node):
        self.stages.append(node)
        stage_id = ''.join([str(s.state_id) for s in self.stages[1:]])
        self.cycle_cond = None
        if self.current_stage.cycle_cond is not None:
            self.cycle_cond = f'cycle_cond_stage_{stage_id}'

        self.exit_cond = None
        if self.current_stage.exit_cond is not None:
            self.exit_cond = f'exit_cond_stage_{stage_id}'

        res = self.visit_IntfBlock(node)

        self.stages.pop()

        stage_id = ''.join([str(s.state_id) for s in self.stages[1:]])
        self.cycle_cond = None
        if self.current_stage.cycle_cond is not None:
            self.cycle_cond = f'cycle_cond_stage_{stage_id}'

        self.exit_cond = None
        if self.current_stage.exit_cond is not None:
            self.exit_cond = f'exit_cond_stage_{stage_id}'

        return res

    def traverse_block(self, svblock, node):
        stmts = self.enter_block(node)

        if isinstance(stmts, list):
            svblock.stmts.extend(stmts)
        elif stmts:
            svblock.stmts.append(stmts)

        for stmt in node.stmts:
            s = self.visit(stmt)
            if isinstance(s, list):
                svblock.stmts.extend(s)
            elif s:
                svblock.stmts.append(s)

        stmts = self.exit_block()

        if isinstance(stmts, list):
            svblock.stmts.extend(stmts)
        elif stmts:
            svblock.stmts.append(stmts)

        # if block isn't empty
        if svblock.stmts:
            self.update_defaults(svblock)
            return svblock

        return None

    def visit_IfElseBlock(self, node):
        if_block = self.visit(node.if_block)
        else_block = self.visit(node.else_block)

        # both blocks empty
        if if_block is None and else_block is None:
            return None

        # only one branch
        if if_block is None or else_block is None:
            if if_block:
                return if_block
            else:
                return else_block

        svblock = SVBlock(
            in_cond=if_block.in_cond,
            else_cond=else_block.in_cond,
            stmts=[if_block, else_block],
            dflts={})

        self.update_defaults(svblock)

        if len(svblock.stmts) != 2:
            # updating defaults can result in removing branches
            if len(svblock.stmts):
                in_cond = svblock.stmts[0].in_cond
            else:
                in_cond = None

            svblock = SVBlock(
                in_cond=in_cond,
                else_cond=None,
                stmts=svblock.stmts,
                dflts=svblock.dflts)

        for i, stmt in enumerate(svblock.stmts):
            tmp = stmt._asdict()
            tmp.pop('in_cond')
            svblock.stmts[i] = SVBlock(in_cond=None, **tmp)

        return svblock

    def visit_Loop(self, node):
        in_cond = None
        if node.in_cond:
            in_cond = svexpr(node.in_cond)
        svblock = SVBlock(in_cond=in_cond, stmts=[], dflts={})
        return self.traverse_block(svblock, node)

    def is_control_var(self, name):
        # control_suffix = ['_en', '_rst', '.valid', '.ready']
        control_suffix = ['_en', '.valid', '.ready']
        for suff in control_suffix:
            if name.endswith(suff):
                return True
        return False

    def update_defaults(self, block):
        # bottom up
        # popagate defaulf values from sub statements to top
        for i, stmt in enumerate(block.stmts):
            if hasattr(stmt, 'dflts'):
                for d in stmt.dflts:
                    # control cannot propagate past in conditions
                    if (not self.is_control_var(d)) or not stmt.in_cond:
                        if d in block.dflts:
                            if block.dflts[d].val is stmt.dflts[d].val:
                                stmt.dflts[d] = None
                        else:
                            block.dflts[d] = stmt.dflts[d]
                            stmt.dflts[d] = None
            elif isinstance(stmt, AssignValue):
                if stmt.target in block.dflts:
                    if block.dflts[stmt.target].val is stmt.val:
                        stmt.val = None
                else:
                    block.dflts[stmt.target] = stmt
                    block.stmts[i] = AssignValue(
                        target=stmt.target, val=None, width=stmt.width)

        self.block_cleanup(block)

        # top down
        # if there are multiple stmts with different in_conds, but same dflt
        for d in block.dflts:
            for stmt in block.stmts:
                if hasattr(stmt, 'dflts') and d in stmt.dflts:
                    if block.dflts[d].val is stmt.dflts[d].val:
                        stmt.dflts[d] = None

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
