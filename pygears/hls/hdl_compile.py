import ast
import inspect

from pygears.typing import Uint, bitw

from . import hdl_types as ht
from .cblock import CBlockVisitor
from .cleanup import condition_cleanup
from .conditions import Conditions
from .hdl_ast import HdlAst
from .hdl_stmt import (AssertionVisitor, BlockConditionsVisitor, InputVisitor,
                       IntfReadyVisitor, IntfValidVisitor, OutputVisitor,
                       RegEnVisitor, StateTransitionVisitor, VariableVisitor)
from .intf_finder import IntfFinder
from .reg_finder import RegFinder
from .scheduling import Scheduler
from .state_finder import BlockId, StateFinder

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


def compose_data(gear, regs, variables, intfs):
    in_ports = {p.basename: ht.IntfDef(p) for p in gear.in_ports}
    named = {}
    for port in in_ports:
        if port in intfs['namedargs']:
            named[port] = in_ports[port]
    hdl_locals = {**named, **intfs['varargs']}
    return ht.ModuleData(
        in_ports=in_ports,
        out_ports={p.basename: ht.IntfDef(p)
                   for p in gear.out_ports},
        hdl_locals=hdl_locals,
        regs=regs,
        variables=variables,
        in_intfs=intfs['vars'],
        out_intfs=intfs['outputs'])


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

    hdl_data = compose_data(gear, reg_v.regs, reg_v.variables, intf.intfs)

    # py ast to hdl ast
    hdl_ast = HdlAst(gear, intf.intfs, hdl_data).visit(body_ast)
    # StmtVacum().visit(hdl_ast)
    schedule = Scheduler().visit(hdl_ast)
    states = StateFinder()
    states.visit(schedule)
    state_num = states.max_state
    BlockId().visit(schedule)

    # from .cblock import pprint
    # pprint(schedule)

    # clear combined conditions from previous run, if any
    Conditions().init()

    block_visitors = {
        'register_next_state': RegEnVisitor(hdl_data),
        'variables': VariableVisitor(hdl_data),
        'outputs': OutputVisitor(hdl_data),
        'inputs': InputVisitor(hdl_data),
        'intf_ready': IntfReadyVisitor(hdl_data),
        'intf_valid': IntfValidVisitor(hdl_data),
        'asssertions': AssertionVisitor(hdl_data),
    }

    res = {}
    for name, visitor in block_visitors.items():
        sub_v = CBlockVisitor(visitor, state_num)
        res[name] = sub_v.visit(schedule)

    if state_num > 0:
        hdl_data.regs['state'] = ht.RegDef(
            name='state', val=Uint[bitw(state_num)](0))
        sub_v = CBlockVisitor(StateTransitionVisitor(hdl_data), state_num)
        res['state_transition'] = sub_v.visit(schedule)

    cond_visit = CBlockVisitor(
        BlockConditionsVisitor(hdl_data=hdl_data, state_num=state_num),
        state_num)
    cond_visit.visit(schedule)

    res['conditions'] = cond_visit.hdl.conditions()
    try:
        from .simplify_expression import simplify_assigns
    except ImportError:
        pass
    else:
        cnt = 3
        while cnt:
            res['conditions'] = simplify_assigns(res['conditions'])
            res = condition_cleanup(res)
            cnt -= 1

    return hdl_data, res
