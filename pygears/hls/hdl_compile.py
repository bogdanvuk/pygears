import ast
import inspect

from pygears.typing import Uint, bitw

from . import hdl_types as ht
from .cblock import CBlockVisitor
from .conditions import Conditions
from .hdl_ast import HdlAst
from .hdl_stmt import (AssertionVisitor, BlockConditionsVisitor, InputVisitor,
                       IntfReadyVisitor, IntfValidVisitor, OutputVisitor,
                       RegEnVisitor, StateTransitionVisitor, VariableVisitor)
from .intf_finder import IntfFinder
from .reg_finder import RegFinder
from .scheduling import Scheduler
from .state_finder import StateFinder

# from .stmt_vacum import StmtVacum


class HDLWriter:
    def __init__(self):
        self.indent = 0
        self.lines = []

    def line(self, line=''):
        if not line:
            self.lines.append('')
        else:
            self.lines.append(f'{" "*self.indent}{line}')

    def block(self, block):
        for line in block.split('\n'):
            self.line(line)


def parse_gear_body(gear):
    body_ast = ast.parse(inspect.getsource(gear.func)).body[0]
    # import astpretty
    # astpretty.pprint(body_ast)

    # find interfaces
    intf = IntfFinder(gear)
    intf.visit(body_ast)

    # find registers and variables
    reg_v = RegFinder(gear, intf.intfs)
    reg_v.visit(body_ast)
    reg_v.clean_variables()

    # py ast to hdl ast
    hdl_ast = HdlAst(gear, reg_v.regs, reg_v.variables,
                     intf.intfs).visit(body_ast)
    # StmtVacum().visit(hdl_ast)
    schedule = Scheduler().visit(hdl_ast)
    states = StateFinder()
    states.visit(schedule)
    state_num = states.max_state

    # from .cblock import pprint
    # pprint(schedule)

    # clear combined conditions from previous run, if any
    Conditions().init()

    block_visitors = {
        'register_next_state': RegEnVisitor(),
        'variables': VariableVisitor(),
        'outputs': OutputVisitor(),
        'inputs': InputVisitor(),
        'intf_ready': IntfReadyVisitor(),
        'intf_valid': IntfValidVisitor(),
        'asssertions': AssertionVisitor(),
    }

    res = {}
    for name, visitor in block_visitors.items():
        sub_v = CBlockVisitor(visitor, state_num)
        res[name] = sub_v.visit(schedule)

    if state_num > 0:
        hdl_ast.data.regs['state'] = ht.RegDef(
            name='state', val=Uint[bitw(state_num)](0))
        sub_v = CBlockVisitor(StateTransitionVisitor(), state_num)
        res['state_transition'] = sub_v.visit(schedule)

    cond_visit = CBlockVisitor(
        BlockConditionsVisitor(reg_num=len(hdl_ast.data.regs), state_num=state_num),
        state_num)
    cond_visit.visit(schedule)

    try:
        from .simplify_expression import simplify_assigns
        res['conditions'] = simplify_assigns(cond_visit.hdl.condition_assigns)
    except ImportError:
        res['conditions'] = cond_visit.hdl.condition_assigns

    return hdl_ast, res
