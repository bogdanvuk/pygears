import ast
import inspect
import typing
from dataclasses import dataclass
from types import FunctionType

from pygears.typing import Uint, bitw

from .assign_conditions import AssignConditions
from .ast_parse import parse_ast
from .cblock import CBlockVisitor
from .cleanup import condition_cleanup
from .conditions_finder import ConditionsFinder
from .conditions_utils import init_conditions
from .hdl_stmt import (AssertionVisitor, InputVisitor, IntfReadyVisitor,
                       IntfValidVisitor, OutputVisitor, RegEnVisitor,
                       VariableVisitor)
from .hls_expressions import IntfDef, RegDef
from .intf_finder import IntfFinder
from .optimizations import pipeline_ast
from .reg_finder import RegFinder
from .scheduling import Scheduler
from .state_finder import BlockId, StateFinder
from .state_transition import HdlStmtStateTransition


@dataclass
class ModuleData:
    in_ports: typing.Dict
    out_ports: typing.Dict
    hdl_locals: typing.Dict
    regs: typing.Dict
    variables: typing.Dict
    in_intfs: typing.Dict
    out_intfs: typing.Dict
    local_namespace: typing.Dict
    gear: typing.Any

    def get_container(self, name):
        for attr in ['regs', 'variables', 'in_intfs', 'out_intfs']:
            data_inst = getattr(self, attr)
            if name in data_inst:
                return data_inst
        # hdl_locals is last because it contain others
        if name in self.hdl_locals:
            return self.hdl_locals
        return None

    def get(self, name):
        data_container = self.get_container(name)
        if data_container is not None:
            return data_container[name]
        return None

    @property
    def optimize(self):
        return self.gear.params['svgen'].get('pipeline', False)

    @property
    def functions(self):
        glob = self.gear.func.__globals__
        return {
            name: value
            for name, value in glob.items() if isinstance(value, FunctionType)
        }


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

    in_ports = {p.basename: IntfDef(p) for p in gear.in_ports}
    hdl_data = ModuleData(
        gear=gear,
        in_ports=in_ports,
        out_ports={p.basename: IntfDef(p)
                   for p in gear.out_ports},
        hdl_locals={},
        regs={},
        variables={},
        in_intfs={},
        out_intfs={},
        local_namespace={
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        })

    # find interfaces
    intf = IntfFinder(hdl_data)
    intf.visit(body_ast)

    # find registers and variables
    reg_v = RegFinder(hdl_data)
    reg_v.visit(body_ast)
    reg_v.clean_variables()

    # py ast to hdl ast
    hdl_ast = parse_ast(body_ast, hdl_data)

    if hdl_data.optimize:
        hdl_ast = pipeline_ast(hdl_ast, hdl_data)

    schedule = Scheduler().visit(hdl_ast)
    states = StateFinder()
    states.visit(schedule)
    state_num = states.max_state
    BlockId().visit(schedule)

    # from .cblock import pprint
    # pprint(schedule)

    # clear combined conditions from previous run, if any
    init_conditions()

    cond_finder = ConditionsFinder(state_num)
    cond_finder.visit(schedule)

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
        hdl_data.regs['state'] = RegDef(
            name='state', val=Uint[bitw(state_num)](0))
        res['state_transition'] = HdlStmtStateTransition(state_num).visit(
            schedule)

    cond_visit = AssignConditions(hdl_data, state_num)
    cond_visit.visit(schedule)

    res['conditions'] = cond_visit.get_condition_block()
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
