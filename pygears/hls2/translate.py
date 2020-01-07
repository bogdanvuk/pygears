from pygears.core.gear import Gear

from . import pydl
from pygears import bind
from pygears.typing import Uint, bitw, Bool
from .schedule import schedule, CBlockVisitor
# from .schedule.state_transition import HdlStmtStateTransition
# from .hdl.visitor import (AssertionVisitor, InputVisitor, IntfReadyVisitor,
#                           IntfValidVisitor, OutputVisitor, RegEnVisitor,
#                           VariableVisitor, FunctionVisitor, OutSigVisitor)
# from .hdl.visitor import InputVisitor, OutputVisitor
from .hdl.visitor import HDLStmtVisitor
from .hdl.nodes import StateBlock, CombBlock
from .hdl.generate import generate

# from .schedule.cleanup import condition_cleanup

# from .schedule.conditions_finder import find_conditions
# from .schedule.conditions_utils import init_conditions


class PydlTestToVar(pydl.PydlVisitor):
    def __init__(self, ctx):
        self.ctx = ctx
        self.ctx.cond_cnt = 0

    def visit_block(self, node):
        for stmt in node.stmts:
            self.visit(stmt)

    def visit_Module(self, node):
        self.top = node

    def generic_visit(self, node):
        pass

    def visit_IfBlock(self, node):
        cond_name = f'cond_{self.ctx.cond_cnt}'
        self.ctx.cond_cnt += 1
        var = pydl.Variable(cond_name, Bool)
        self.ctx.scope[cond_name] = var
        self.top.stmts.append(pydl.Assign(var, node.test))

    def visit_ElseBlock(self, node):
        return self.visit_IfBlock(node)

    def visit_all_Expr(self, node):
        return None


def translate_gear(gear: Gear):
    bind('gear/exec_context', 'hls')

    # For the code that inspects gear via module() call
    bind('gear/current_module', gear)

    pydl_ast, ctx = pydl.translate_gear(gear)

    schedule_ctx = schedule(pydl_ast)
    ctx.state_root = schedule_ctx.state_root
    ctx.stmt_states = schedule_ctx.stmt_states

    res = generate(pydl_ast, ctx)

    bind('gear/exec_context', 'compile')
    return ctx, res
