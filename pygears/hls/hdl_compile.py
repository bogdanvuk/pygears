import ast
import typing
import astpretty
import inspect
from dataclasses import dataclass, field
from types import FunctionType
from itertools import chain

from pygears.typing import Uint, bitw
from pygears.core.util import get_function_context_dict

from .utils import get_function_source, hls_debug, hls_debug_header, hls_debug_log_enabled
from .assign_conditions import AssignConditions
from .ast_parse import parse_ast, parse_block
from .cblock import CBlockVisitor
from .cleanup import condition_cleanup
from .conditions_finder import find_conditions
from .conditions_utils import init_conditions
from .hdl_stmt import (AssertionVisitor, InputVisitor, IntfReadyVisitor,
                       IntfValidVisitor, OutputVisitor, RegEnVisitor,
                       VariableVisitor, FunctionVisitor)
from .hls_expressions import IntfDef, RegDef, VariableDef, VariableStmt, OperandVal, ReturnStmt
from .intf_finder import IntfFinder
from .optimizations import pipeline_ast
from .reg_finder import RegFinder
from .scheduling import Scheduler
from .state_finder import BlockId, StateFinder
from .state_transition import HdlStmtStateTransition
from .pydl_types import pformat as pydl_pformat
from .pydl_types import Function
from .cblock import pformat as cblock_pformat
from pygears.core.infer_ftypes import infer_ftypes


@dataclass
class ModuleData:
    in_ports: typing.Dict
    out_ports: typing.Dict
    hdl_locals: typing.Dict
    regs: typing.Dict
    variables: typing.Dict
    in_intfs: typing.Dict
    out_intfs: typing.Dict
    gear: typing.Any
    func: typing.Any
    hdl_functions: typing.Dict
    hdl_functions_impl: typing.Dict = field(default_factory=dict)
    context: typing.List = field(default_factory=list)
    _local_namespace: typing.Dict = None

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

    def add_variable(self, name, dtype):
        self.variables[name] = VariableDef(val=dtype, name=name)

    @property
    def current_block(self):
        return self.context[-1]

    @property
    def optimize(self):
        return self.gear.params['hdl'].get('pipeline', False)

    @property
    def local_namespace(self):
        if self._local_namespace is None:
            self._local_namespace = {}
            for name, value in chain(
                    get_function_context_dict(self.func).items(),
                    self.gear.explicit_params.items()):

                self._local_namespace[name] = value

        return self._local_namespace


def clean_variables(hdl_data):
    # removes unused variables
    # for instance: variable in an if False block
    hdl_data.variables = {
        key: val
        for key, val in hdl_data.variables.items()
        if not isinstance(val, ast.AST)
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


def print_parse_intro(gear, body_ast, source):
    hls_debug('*' * 80)
    hls_debug_header(f'Compiling code for the gear "{gear.name}" of the type '
                     f'"{gear.definition.__name__}"')

    fn = inspect.getfile(gear.func)
    try:
        _, ln = inspect.getsourcelines(gear.func)
    except OSError:
        ln = '-'

    hls_debug(
        source,
        title=f'Parsing function "{gear.func.__name__}" from "{fn}", line {ln}'
    )

    hls_debug_header('Function body AST')

    for stmt in body_ast.body:
        hls_debug(stmt)


@parse_ast.register(ast.FunctionDef)
def parse_func(node, module_data):
    if hasattr(node, 'func'):
        func = node.func
    else:
        func = module_data.local_namespace[node.name]

    func_hdl_data = ModuleData(gear=module_data.gear,
                               func=func,
                               in_ports={},
                               out_ports={},
                               hdl_locals={},
                               hdl_functions={},
                               regs={},
                               variables=None,
                               in_intfs={},
                               out_intfs={})

    if hls_debug_log_enabled():
        hls_debug(
            {
                k: v
                for k, v in func_hdl_data.local_namespace.items()
                if k != '__builtins__'
            },
            title='Function local namespace')

    inputs = {}
    func_hdl_data.hdl_locals = {}
    for arg in node.args.args:
        name = arg.arg

        dtype = arg.annotation
        if isinstance(dtype, (str, bytes)):
            dtype = eval(dtype, func_hdl_data.local_namespace)

        var = VariableDef(val=dtype, name=name)
        inputs[name] = OperandVal(var, 'v')
        func_hdl_data.hdl_locals[name] = var

    ret_dtype = None
    if func.__annotations__:
        params = {**func.__annotations__}
        for name, var in inputs.items():
            if name not in params:
                params[name] = var.dtype

        res = infer_ftypes(
            params=params,
            args={name: var.dtype
                  for name, var in inputs.items()},
            namespace=func_hdl_data.local_namespace)

        ret_dtype = res.get('return', None)

    func_hdl_data.variables = {**inputs}

    if func_hdl_data.variables:
        hls_debug(func_hdl_data.variables, title='Found Variables')

    pydl_node = Function(stmts=[],
                         args=inputs,
                         name=node.name,
                         ret_dtype=ret_dtype,
                         hdl_data=func_hdl_data)

    parse_block(pydl_node, node.body, func_hdl_data)

    if pydl_node.ret_dtype is None:
        for stmt in pydl_node.stmts:
            if not isinstance(stmt, ReturnStmt):
                continue

            pydl_node.ret_dtype = stmt.val.dtype

    if hls_debug_log_enabled():
        hls_debug(pydl_pformat(pydl_node), title='Function PyDL AST')

    return pydl_node


def parse_gear_body(gear):
    # from .utils import hls_enable_debug_log
    # hls_enable_debug_log()

    source = get_function_source(gear.func)
    body_ast = ast.parse(source).body[0]

    print_parse_intro(gear, body_ast, source)

    in_ports = {p.basename: IntfDef(p) for p in gear.in_ports}

    hdl_data = ModuleData(
        gear=gear,
        func=gear.func,
        in_ports=in_ports,
        out_ports={p.basename: IntfDef(p)
                   for p in gear.out_ports},
        hdl_locals={},
        hdl_functions={},
        regs={},
        variables={},
        in_intfs={},
        out_intfs={})

    hdl_data.local_namespace.update(
        {p.basename: p.consumer
         for p in gear.in_ports})
    hdl_data.local_namespace.update(gear.explicit_params)
    hdl_data.local_namespace['module'] = lambda: gear

    # find interfaces
    intf = IntfFinder(hdl_data)
    intf.visit(body_ast)

    if hls_debug_log_enabled():
        hls_debug(
            {
                k: v
                for k, v in hdl_data.local_namespace.items()
                if k != '__builtins__'
            },
            title='Function local namespace')

    # find registers and variables
    reg_v = RegFinder(hdl_data)
    reg_v.visit(body_ast)
    reg_v.clean_variables()

    if hdl_data.regs:
        hls_debug(hdl_data.regs, title='Found registers')

    if hdl_data.variables:
        hls_debug(hdl_data.variables, title='Found Variables')

    # py ast to hdl ast
    hdl_ast = parse_ast(body_ast, hdl_data)
    clean_variables(hdl_data)

    if hls_debug_log_enabled():
        hls_debug(pydl_pformat(hdl_ast), title='PyDL AST')

    if hdl_data.optimize:
        hdl_ast = pipeline_ast(hdl_ast, hdl_data)

    schedule = Scheduler().visit(hdl_ast)
    states = StateFinder()
    states.visit(schedule)
    state_num = states.max_state
    BlockId().visit(schedule)

    if hls_debug_log_enabled():
        hls_debug(cblock_pformat(schedule), title='State Structure')

    # clear combined conditions from previous run, if any
    init_conditions()

    find_conditions(schedule, state_num)

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
        sub_v = CBlockVisitor(visitor)
        res[name] = sub_v.visit(schedule)

    if state_num > 0:
        hdl_data.regs['state'] = RegDef(name='state',
                                        val=Uint[bitw(state_num)](0))
        res['state_transition'] = HdlStmtStateTransition(state_num).visit(
            schedule)

    cond_visit = AssignConditions(hdl_data, state_num)
    cond_visit.visit(schedule)

    for name, func_block in hdl_data.hdl_functions_impl.items():
        hdl_data.hdl_functions[name] = FunctionVisitor(
            func_block.hdl_data).visit(func_block)

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
