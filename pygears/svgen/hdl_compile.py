import ast
import inspect
import os

import hdl_types as ht
from pygears.definitions import ROOT_DIR
from pygears.typing import Uint, bitw

from .cblock import CBlockVisitor
from .hdl_ast import HdlAst
from .hdl_stmt import (BlockConditionsVisitor, InputVisitor, IntfReadyVisitor,
                       IntfValidVisitor, OutputVisitor, RegEnVisitor,
                       StateTransitionVisitor, VariableVisitor)
from .intf_finder import IntfFinder
from .reg_finder import RegFinder
from .scheduling import Scheduler
from .simplify_expression import simplify_assigns
from .state_finder import StateFinder

# from .stmt_vacum import StmtVacum


class HDLWriter:
    def __init__(self):
        self.indent = 0
        self.svlines = []

    def line(self, line=''):
        if not line:
            self.svlines.append('')
        else:
            self.svlines.append(f'{" "*self.indent}{line}')

    def block(self, block):
        for line in block.split('\n'):
            self.line(line)


def parse_gear_body(gear, function_impl_paths=None):
    common_func_impl = os.path.abspath(
        os.path.join(ROOT_DIR, 'svgen', 'hdl_ast_functions.py'))
    if function_impl_paths is None:
        function_impl_paths = [common_func_impl]
    else:
        function_impl_paths.append(common_func_impl)

    body_ast = ast.parse(inspect.getsource(gear.func)).body[0]
    # import astpretty
    # astpretty.pprint(body_ast)

    # find interfaces
    intf = IntfFinder(gear)
    intf.visit(body_ast)

    # find registers and variables
    v = RegFinder(gear, intf.intfs['varargs'], intf.intfs['outputs'])
    v.visit(body_ast)
    v.clean_variables()

    # py ast to hdl ast
    hdl_ast = HdlAst(gear, v.regs, v.variables, intf.intfs,
                     function_impl_paths).visit(body_ast)
    # StmtVacum().visit(hdl_ast)
    schedule = Scheduler().visit(hdl_ast)
    states = StateFinder()
    states.visit(schedule)
    state_num = states.max_state

    # from .cblock import pprint
    # pprint(schedule)

    block_visitors = {
        'register_next_state': RegEnVisitor(),
        'variables': VariableVisitor(),
        'outputs': OutputVisitor(),
        'inputs': InputVisitor(),
        'intf_ready': IntfReadyVisitor(),
        'intf_valid': IntfValidVisitor()
    }

    res = {}
    cycle_conds = []
    exit_conds = []
    for name, visitor in block_visitors.items():
        sub_v = CBlockVisitor(visitor, state_num)
        res[name] = sub_v.visit(schedule)
        cycle_conds.extend(list(set(sub_v.cycle_conds)))
        exit_conds.extend(list(set(sub_v.exit_conds)))

    if state_num > 0:
        hdl_ast.regs['state'] = ht.RegDef(
            name='state', val=Uint[bitw(state_num)](0))
        sub_v = CBlockVisitor(StateTransitionVisitor(), state_num)
        res['state_transition'] = sub_v.visit(schedule)
        cycle_conds.extend(list(set(sub_v.cycle_conds)))
        exit_conds.extend(list(set(sub_v.exit_conds)))

    cycle_conds = list(set(cycle_conds))
    exit_conds = list(set(exit_conds))

    cond_visit = CBlockVisitor(
        BlockConditionsVisitor(
            cycle_conds,
            exit_conds,
            reg_num=len(hdl_ast.regs),
            state_num=state_num), state_num)
    cond_visit.visit(schedule)
    res['conditions'] = simplify_assigns(cond_visit.hdl.condition_assigns)
    # res['conditions'] = cond_visit.hdl.condition_assigns

    return hdl_ast, res
