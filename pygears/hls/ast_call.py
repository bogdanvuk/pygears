import ast
import inspect

from types import FunctionType
from pygears import Intf
from pygears.typing import Unit, is_type, typeof
from pygears.core.util import is_standard_func
from pygears.core.util import get_function_context_dict

from .hdl_builtins import builtins
from .ast_parse import parse_ast
from .hls_expressions import ConcatExpr, FunctionCall, OperandVal, ResExpr
from .hls_expressions import Expr, IntfDef
from .utils import (VisitError, add_to_list, eval_expression,
                    find_data_expression, find_target, get_context_var,
                    get_function_ast, get_function_source, hls_debug,
                    hls_debug_header)


@parse_ast.register(ast.Call)
def parse_call(node, module_data):
    arg_unpacked = []
    for arg in node.args:
        if isinstance(arg, ast.Starred):
            var = get_context_var(arg.value.id, module_data)

            if not isinstance(var, ConcatExpr):
                raise VisitError(f'Cannot unpack variable "{arg.value.id}"')

            for i in range(len(var.operands)):
                arg_unpacked.append(
                    ast.fix_missing_locations(
                        ast.Subscript(value=arg.value,
                                      slice=ast.Index(value=ast.Num(i)),
                                      ctx=ast.Load)))
        else:
            arg_unpacked.append(arg)

    arg_nodes = [
        find_data_expression(arg, module_data) for arg in arg_unpacked
    ]

    func_args = arg_nodes
    if all(isinstance(node, ResExpr) for node in arg_nodes):
        func_args = []
        for arg in arg_nodes:
            if is_type(type(arg.val)) and not typeof(type(arg.val), Unit):
                func_args.append(str(int(arg.val)))
            else:
                func_args.append(str(arg.val))

    try:
        ret = eval(f'{node.func.id}({", ".join(func_args)})',
                   module_data.local_namespace)
        return ResExpr(ret)
    except:
        return parse_func_call(node, func_args, module_data)


def parse_function(func, module_data):
    hls_debug_header(f'Parsing function call to "{func.__name__}"')
    source = get_function_source(func)
    hls_debug(source, title='Function source:')

    func_ast = get_function_ast(func)

    hls_debug(func_ast, title='Function AST:')

    return func_ast


def inline_function(func, args, kwds, module_data, returns):
    hls_debug_header(f'Inlining function call to "{func.__name__}"')
    source = get_function_source(func)
    hls_debug(source, title='Function source:')

    if kwds:
        pass

    def find_original_arguments(args, new_names, kwargs):
        arg_names = {}
        arg_names.update(kwargs)  # passed as keyword arguments

        # passed arguments
        for arg, replace in zip(args.args, new_names):
            arg_names[arg.arg] = replace

        # default values
        for arg, dflt in zip(reversed(args.args), reversed(args.defaults)):
            if arg.arg not in arg_names:
                arg_names[arg.arg] = dflt

        return arg_names

    if not is_standard_func(func):
        raise VisitError(f'Only standard functions are supported!')

    func_ast = get_function_ast(func)

    replace_kwds = {n.arg: n.value.id for n in kwds}

    arguments = []
    for arg in args:
        if isinstance(arg, ast.Starred):
            var = get_context_var(arg.value.id, module_data)

            if not isinstance(var, ConcatExpr):
                raise VisitError(f'Cannot unpack variable "{arg.value.id}"')

            for i in range(len(var.operands)):
                arguments.append(
                    ast.fix_missing_locations(
                        ast.Subscript(value=arg.value,
                                      slice=ast.Index(value=ast.Num(i)),
                                      ctx=ast.Load)))
        else:
            arguments.append(arg)

    argument_map = find_original_arguments(func_ast.args, arguments,
                                           replace_kwds)

    hls_debug_header('Arguments map')

    for name, arg in argument_map.items():
        hls_debug(f'"{name}"', indent=4)
        hls_debug(arg, indent=8)

    AstFunctionReplace(argument_map, returns,
                       get_function_context_dict(func)).visit(func_ast)
    func_ast = ast.fix_missing_locations(func_ast)

    hls_debug(func_ast, title='Function inlined AST:')

    body = func_ast.body

    res = []
    for stmt in body:
        res_stmt = parse_ast(stmt, module_data)
        add_to_list(res, res_stmt)
    return res


class AstFunctionReplace(ast.NodeTransformer):
    def __init__(self, args, returns, context):
        self.args = args
        self.returns = returns
        self.context = context

    def visit_Name(self, node):
        if node.id in self.args:
            switch_val = self.args[node.id]
            if not isinstance(switch_val, str):
                return switch_val
            node.id = switch_val

        elif node.id in self.context:
            val = self.context[node.id]
            try:
                return ast.Num(val.code())
            except (AttributeError, TypeError):
                pass

            if isinstance(val, int):
                return ast.Num(int(val))

        return node

    def visit_Return(self, node):
        self.visit(node.value)

        try:
            targets = find_target(node.value)
            if targets == self.returns:
                return None
        except (AttributeError, VisitError):
            pass

        ret_targets = [ast.Name(name, ast.Load()) for name in self.returns]
        return ast.fix_missing_locations(ast.Assign(ret_targets, node.value))


def parse_func_call(node, func_args, module_data):
    try:
        func = eval_expression(node.func, module_data.local_namespace)
    except:
        if isinstance(node.func, ast.Attribute):
            obj = find_data_expression(node.func.value, module_data)
            if isinstance(obj, IntfDef):
                func = getattr(Intf, node.func.attr)
            else:
                func = getattr(obj.dtype, node.func.attr)

            func_args = [obj] + func_args
        else:
            func = module_data.hdl_functions[node.func.id]

    # If we are dealing with bound methods
    if not inspect.isbuiltin(func) and hasattr(func, '__self__'):
        obj = func.__self__
        if isinstance(func.__self__, Intf):
            obj = find_data_expression(node.func.value, module_data)

        func_args = [obj] + func_args
        func = getattr(type(func.__self__), func.__name__)

    if func in builtins:
        func = builtins[func](*func_args)
    elif is_type(func):
        from .hdl_arith import resolve_cast_func
        func = resolve_cast_func(func, func_args[0])

    if func is None or isinstance(func, Expr):
        return func

    if not isinstance(func, FunctionType):
        raise VisitError('Unrecognized func in call')

    if hasattr(node.func, 'id'):
        func_name = node.func.id
    else:
        func_name = func.__name__

    while func_name in module_data.hdl_functions_impl:
        func_name += '_'

    arg_unpacked = []
    for arg in node.args:
        if isinstance(arg, ast.Starred):
            var = get_context_var(arg.value.id, module_data)

            if not isinstance(var, ConcatExpr):
                raise VisitError(f'Cannot unpack variable "{arg.value.id}"')

            for i in range(len(var.operands)):
                arg_unpacked.append(
                    ast.fix_missing_locations(
                        ast.Subscript(value=arg.value,
                                      slice=ast.Index(value=ast.Num(i)),
                                      ctx=ast.Load)))
        else:
            arg_unpacked.append(arg)

    arg_unpacked = arg_unpacked[:len(inspect.getfullargspec(func).args)]
    func_args = func_args[:len(inspect.getfullargspec(func).args)]

    if func.__name__ != '<lambda>':
        func_ast = parse_function(func, module_data)
        func_ast.name = func_name
        func_ast.func = func
        func_params = func_ast.args.args

        if len(func_params) != len(func_args):
            raise VisitError(
                f'Wrong number of arguments when calling function "{func_name}"'
            )

        for param, arg in zip(func_params, func_args):
            param.annotation = arg.dtype

        module_data.hdl_functions_impl[func_name] = parse_ast(
            func_ast, module_data)

        return FunctionCall(
            operands=func_args,
            ret_dtype=module_data.hdl_functions_impl[func_name].ret_dtype,
            name=func_name)

    else:
        var_name = f'{func_name}_res'
        module_data.variables[var_name] = None

        res = inline_function(func,
                              arg_unpacked, {},
                              module_data,
                              returns=[var_name])

        module_data.add_variable(var_name, res[0].dtype)

        module_data.current_block.stmts.extend(res)

        return OperandVal(op=module_data.variables[var_name], context='v')
