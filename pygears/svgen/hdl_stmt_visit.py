import typing as pytypes
from dataclasses import dataclass

import hdl_types as ht
from pygears.typing.base import TypingMeta

from .cblock import add_to_list
from .inst_visit import InstanceVisitor


@dataclass
class AssignValue:
    target: pytypes.Any
    val: pytypes.Any
    width: TypingMeta = None


@dataclass
class CombBlock:
    stmts: pytypes.List
    dflts: pytypes.Dict


@dataclass
class HDLBlock:
    stmts: pytypes.List
    dflts: pytypes.Dict
    in_cond: str = None
    else_cond: str = None


class HDLStmtVisitor(InstanceVisitor):
    def __init__(self):
        self.scope = []

    @property
    def current_scope(self):
        return self.scope[-1]

    def generic_visit(self, node):
        pass

    def set_conditions(self):
        self.cycle_cond = None
        if self.current_scope.cycle_cond is not None:
            self.cycle_cond = f'cycle_cond_block_{self.current_scope.id}'
        self.exit_cond = None
        if self.current_scope.exit_cond is not None:
            self.exit_cond = f'exit_cond_block_{self.current_scope.id}'

    def enter_block(self, block):
        self.scope.append(block)
        self.set_conditions()

    def exit_block(self):
        self.scope.pop()
        self.set_conditions()

    def visit_Module(self, node):
        block = CombBlock(stmts=[], dflts={})
        return self.traverse_block(block, node)

    def visit_IntfBlock(self, node):
        return self.visit_block(node)

    def visit_IntfLoop(self, node):
        return self.visit_block(node)

    def visit_IfBlock(self, node):
        return self.visit_block(node)

    def visit_IfElseBlock(self, node):
        if_block = self.visit(node.if_block)
        else_block = self.visit(node.else_block)

        block = HDLBlock(
            in_cond=if_block.in_cond,
            else_cond=else_block.in_cond,
            stmts=[if_block, else_block],
            dflts={})

        self.update_defaults(block)

        return block

    def visit_Loop(self, node):
        return self.visit_block(node)

    def visit_YieldBlock(self, node):
        return self.visit_block(node)

    def visit_block(self, node):
        block = HDLBlock(in_cond=node.in_cond, stmts=[], dflts={})
        return self.traverse_block(block, node)

    def traverse_block(self, block, node):
        add_to_list(block.stmts, self.enter_block(node))

        # if block isn't empty
        if block.stmts:
            self.update_defaults(block)

        return block

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


class RegEnVisitor(HDLStmtVisitor):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return [AssignValue(f'{reg}_en', 0) for reg in block.regs]

    def visit_RegNextStmt(self, node):
        return [
            AssignValue(target=f'{node.reg.name}_en', val=self.cycle_cond),
            AssignValue(
                target=f'{node.reg.name}_next',
                val=node.val,
                width=int(node.reg.dtype))
        ]


class VariableVisitor(HDLStmtVisitor):
    def visit_VariableStmt(self, node):
        return AssignValue(
            target=f'{node.variable.name}_v',
            val=node.val,
            width=int(node.variable.dtype))


class OutputVisitor(HDLStmtVisitor):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return AssignValue(f'dout.valid', 0)

    def visit_YieldStmt(self, node):
        return [
            AssignValue(f'dout.valid', 1),
            AssignValue(f'dout_s', node.expr, int(node.expr.dtype))
        ]


class InputVisitor(HDLStmtVisitor):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return [
                AssignValue(f'{port.name}.ready', 0) for port in block.in_ports
            ]
        elif isinstance(block, ht.IntfBlock):
            return AssignValue(
                target=f'{block.intf.name}.ready', val=self.exit_cond)
        elif isinstance(block, ht.IntfLoop):
            return AssignValue(
                target=f'{block.intf.name}.ready', val=self.cycle_cond)


class BlockConditionsVisitor(HDLStmtVisitor):
    def __init__(self):
        super().__init__()
        self.cycle_conds = []
        self.exit_conds = []

    def get_cycle_cond(self):
        if self.current_scope.id not in self.cycle_conds:
            self.cycle_conds.append(self.current_scope.id)
            return AssignValue(
                target=f'cycle_cond_block_{self.current_scope.id}',
                val=self.current_scope.cycle_cond)

    def get_exit_cond(self):
        if self.current_scope.id not in self.exit_conds:
            self.exit_conds.append(self.current_scope.id)
            return AssignValue(
                target=f'exit_cond_block_{self.current_scope.id}',
                val=self.current_scope.exit_cond)

    def enter_block(self, block):
        super().enter_block(block)

        if isinstance(block, ht.IntfBlock):
            return self.get_exit_cond()

        if isinstance(block, ht.IntfLoop):
            return self.get_cycle_cond()

    def visit_RegNextStmt(self, node):
        return self.get_cycle_cond()
