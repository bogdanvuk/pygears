import typing as pytypes
from pygears.typing.base import TypingMeta
from .hdl_ast import Module, RegNextExpr
from pygears.typing import Array, typeof, Integer


class AssignValue(pytypes.NamedTuple):
    target: pytypes.Any
    val: pytypes.Any
    width: TypingMeta


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
        raise Exception
        # for field, value in ast.iter_fields(node):
        #     if isinstance(value, list):
        #         for item in value:
        #             if isinstance(item, ast.AST):
        #                 self.visit(item)
        #     elif isinstance(value, ast.AST):
        #         self.visit(value)


class SVCompilerPreprocess(InstanceVisitor):
    def __init__(self, visit_var, dflts=None):
        self.svlines = []
        self.scope = []
        self.dflts = dflts
        self.visit_var = visit_var

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def write_reg_enable(self, name, node, cond):
        if name in self.module.regs:
            # register is enabled if it is assigned in the current block
            for stmt in node.stmts:
                if isinstance(stmt, RegNextExpr) and (stmt.reg.svrepr == name):
                    return AssignValue(target=f'{name}_en', val=cond, width=1)

    def visit_Module(self, node):
        self.module = node
        comb_block = CombBlock(stmts=[], dflts={})
        self.enter_block(node)

        for d in self.dflts:
            comb_block.dflts[f'{self.visit_var}{d}'] = AssignValue(
                f'{self.visit_var}{d}', 0, 1)
        for stmt in node.stmts:
            s = self.visit(stmt)
            if s:
                comb_block.stmts.append(s)

        self.exit_block()
        self.update_defaults(comb_block)
        return comb_block

    def find_out_conds(self, halt_on):
        out_cond = []
        for block in reversed(self.scope):
            if isinstance(block, Module):
                break

            out_cond += getattr(block, 'cycle_cond', [])

            if (halt_on == 'cycle') and getattr(block, 'exit_cond', []):
                break

            if getattr(block, 'exit_cond', []):
                out_cond += getattr(block, 'exit_cond', [])

        out_cond_svrepr = ' && '.join(cond.svrepr for cond in out_cond)

        return out_cond_svrepr

    def find_cycle_cond(self):
        return self.find_out_conds(halt_on='cycle')

    def find_exit_cond(self):
        return self.find_out_conds(halt_on='exit')

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]

        svrepr = (f"({int(node.dtype)})'({ops[0]})"
                  f" {node.operator} "
                  f"({int(node.dtype)})'({ops[1]})")
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
        return f'{node.intf.basename}_s'

    def visit_Yield(self, node):
        for port in self.module.out_ports:
            if port.name == self.visit_var:
                name = self.visit(node.expr)
                return SVBlock(
                    dflts={
                        f'{self.visit_var}.valid':
                        AssignValue(f'{self.visit_var}.valid', 1, 1),
                        f'{self.visit_var}_s':
                        AssignValue(f'{self.visit_var}_s', name,
                                    int(node.expr.dtype))
                    },
                    stmts=[])

    def visit_RegNextExpr(self, node):
        if node.reg.svrepr == self.visit_var:
            return AssignValue(
                target=f'{self.visit_var}_next',
                val=node.svrepr,
                width=int(node.reg.dtype))

    def visit_VariableExpr(self, node):
        if node.variable.svrepr == self.visit_var:
            return AssignValue(
                target=f'{self.visit_var}_v',
                val=node.svrepr,
                width=int(node.variable.dtype))

    def visit_IntfBlock(self, node):
        svblock = SVBlock(
            in_cond=f'{self.visit(node.in_cond)}.valid', stmts=[], dflts={})
        return self.traverse_block(svblock, node)

    def visit_Block(self, node):
        svblock = SVBlock(
            in_cond=node.in_cond.svrepr if node.in_cond else None,
            stmts=[],
            dflts={})
        return self.traverse_block(svblock, node)

    def traverse_block(self, svblock, node):
        var_is_reg = (self.visit_var in self.module.regs)
        var_is_port = False
        for port in self.module.in_ports:
            if self.visit_var == port.name:
                var_is_port = True

        self.enter_block(node)

        if node.cycle_cond or getattr(node, 'exit_cond', []):
            cycle_cond = self.find_cycle_cond()
            exit_cond = self.find_exit_cond()

            if exit_cond and var_is_reg:
                svblock.stmts.append(
                    AssignValue(
                        target=f'{self.visit_var}_rst', val=exit_cond,
                        width=1))

            if cycle_cond:
                cond = cycle_cond
                if getattr(node, 'multicycle', None) and exit_cond:
                    if self.visit_var not in node.multicycle:
                        cond = exit_cond

                if var_is_port:
                    if not node.in_cond or (
                            self.visit_var in node.in_cond.svrepr):
                        svblock.stmts.append(
                            AssignValue(
                                target=f'{self.visit_var}.ready',
                                val=cond,
                                width=1))
                elif var_is_reg:
                    s = self.write_reg_enable(self.visit_var, node, cond)
                    if s:
                        svblock.stmts.append(s)

        if not node.cycle_cond or not self.find_cycle_cond():
            # TODO ?
            if var_is_port:
                if not node.in_cond or (self.visit_var in node.in_cond.name):
                    svblock.stmts.append(
                        AssignValue(
                            target=f'{self.visit_var}.ready', val=1, width=1))

            if var_is_reg:
                s = self.write_reg_enable(self.visit_var, node, 1)
                if s:
                    svblock.stmts.append(s)

        for stmt in node.stmts:
            s = self.visit(stmt)
            if s:
                svblock.stmts.append(s)

        self.exit_block()

        # if block isn't empty
        if svblock.stmts:
            self.update_defaults(svblock)
            return svblock

        return None

    def visit_IfElseBlock(self, node):
        assert len(node.stmts) == 2
        blocks = []
        for stmt in node.stmts:
            blocks.append(self.visit_Block(stmt))

        # both blocks empty
        if all(b is None for b in blocks):
            return None

        # only one branch
        if any(b is None for b in blocks):
            for b in blocks:
                if b is not None:
                    return b

        svblock = SVBlock(
            in_cond=blocks[0].in_cond,
            else_cond=blocks[1].in_cond,
            stmts=[],
            dflts={})

        for b in blocks:
            svblock.stmts.append(b)

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
        return self.visit_Block(node)

    def is_control_var(self, name):
        control_suffix = ['_en', '_rst', '.valid', '.ready']
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
