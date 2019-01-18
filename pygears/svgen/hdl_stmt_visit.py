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

    def generic_visit(self, node):
        # TODO allow all expresions
        assert isinstance(node, ht.Yield)
        return None

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def visit_Module(self, node):
        block = CombBlock(stmts=[], dflts={})
        return self.traverse_block(block, node)

    def visit_IntfBlock(self, node):
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

    def visit_Yield(self, node):
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
        elif hasattr(block, 'intf'):
            return AssignValue(
                target=f'{block.intf.name}.ready', val=block.cycle_cond)


class StageConditionsVisitor(HDLStmtVisitor):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return [
                AssignValue(f'cycle_cond_stage_{stage.stage_id}', 1)
                for stage in block.stages
            ]

    def generic_visit(self, node):
        if hasattr(node, 'cycle_cond') and node.cycle_cond is not None:
            return AssignValue(
                target=f'cycle_cond_stage_{self.current_stage.stage_id}',
                val=node.cycle_cond)
