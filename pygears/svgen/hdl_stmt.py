import typing as pytypes
from dataclasses import dataclass

import hdl_types as ht
from pygears.typing.base import TypingMeta

from .hdl_utils import add_to_list


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


@dataclass
class HDLStmtVisitor:
    def visit(self, node, conds, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ is 'generic_visit' and isinstance(node, ht.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ is 'generic_visit' and isinstance(node, ht.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        return visitor(node, conds, **kwds)

    def generic_visit(self, node, conds, **kwds):
        pass

    def enter_block(self, block, conds, **kwds):
        self.current_scope = block

    def exit_block(self):
        pass

    def visit_Module(self, node, conds, **kwds):
        block = CombBlock(stmts=[], dflts={})
        return self.traverse_block(block, node, conds, **kwds)

    def visit_ContainerBlock(self, node, conds, **kwds):
        return HDLBlock(in_cond=None, stmts=[], dflts={})

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
                    if block.dflts[d].val == stmt.dflts[d].val:
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
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            return [AssignValue(f'{reg}_en', 0) for reg in block.regs]

    def visit_RegNextStmt(self, node, conds, **kwds):
        return [
            AssignValue(target=f'{node.reg.name}_en', val=conds.cycle_cond),
            AssignValue(
                target=f'{node.reg.name}_next',
                val=node.val,
                width=int(node.reg.dtype))
        ]


class VariableVisitor(HDLStmtVisitor):
    def visit_VariableStmt(self, node, conds, **kwds):
        return AssignValue(
            target=f'{node.variable.name}_v',
            val=node.val,
            width=int(node.variable.dtype))


class OutputVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            return AssignValue(f'dout.valid', 0)

    def visit_Yield(self, node, conds, **kwds):
        block = HDLBlock(
            in_cond=None,
            stmts=[
                AssignValue(f'dout.valid', 1),
                AssignValue(f'dout_s', node.expr, int(node.expr.dtype))
            ],
            dflts={})
        self.update_defaults(block)
        return block


class InputVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            return [
                AssignValue(f'{port.name}.ready', 0) for port in block.in_ports
            ]
        elif isinstance(block, ht.IntfBlock):
            return AssignValue(
                target=f'{block.intf.name}.ready', val=conds.exit_cond)
        elif isinstance(block, ht.IntfLoop):
            return AssignValue(
                target=f'{block.intf.name}.ready', val=conds.cycle_cond)


class BlockConditionsVisitor(HDLStmtVisitor):
    def __init__(self, cycle_conds, exit_conds):
        super().__init__()
        self.cycle_conds = list(tuple(cycle_conds))
        self.exit_conds = list(tuple(exit_conds))
        self.condition_assigns = CombBlock(stmts=[], dflts={})

    def get_cycle_cond(self):
        if self.current_scope.id in self.cycle_conds:
            self.cycle_conds.remove(self.current_scope.id)
            cond = self.current_scope.cycle_cond
            if cond is None:
                cond = 1
            self.condition_assigns.stmts.append(
                AssignValue(
                    target=f'cycle_cond_block_{self.current_scope.id}',
                    val=cond))

    def get_exit_cond(self):
        if self.current_scope.id in self.exit_conds:
            self.exit_conds.remove(self.current_scope.id)
            cond = self.current_scope.exit_cond
            if cond is None:
                cond = 1
            self.condition_assigns.stmts.append(
                AssignValue(
                    target=f'exit_cond_block_{self.current_scope.id}',
                    val=cond))

    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        self.get_cycle_cond()
        self.get_exit_cond()


class StateTransitionVisitor(HDLStmtVisitor):
    def enter_block(self, block, conds, **kwds):
        super().enter_block(block, conds, **kwds)
        if isinstance(block, ht.Module):
            return AssignValue(f'state_en', 0)

    def visit_all_Block(self, node, conds, **kwds):
        block = super().visit_all_Block(node, conds, **kwds)

        if 'state_id' in kwds:
            add_to_list(block.stmts, [
                AssignValue(target=f'state_en', val=node.exit_cond),
                AssignValue(target='state_next', val=kwds['state_id'])
            ])
            if block.stmts:
                self.update_defaults(block)

        return block
