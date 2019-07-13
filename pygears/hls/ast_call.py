import ast
from functools import reduce

from pygears import registry
from pygears.typing import Int, Tuple, Uint, Unit, is_type, typeof
from pygears.core.util import is_standard_func
from pygears.core.util import get_function_context_dict

from .ast_parse import parse_ast
from .hls_expressions import (ArrayOpExpr, AttrExpr, BinOpExpr, CastExpr,
                              ConcatExpr, ConditionalExpr, IntfDef, ResExpr,
                              UnaryOpExpr, OperandVal, FunctionCall)
from .utils import (VisitError, add_to_list, cast_return, eval_expression,
                    find_data_expression, find_target, set_pg_type,
                    get_function_ast, get_context_var, hls_debug_header,
                    hls_debug, get_function_source)


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
        ret = eval(f'{node.func.id}({", ".join(func_args)})')
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


def max_expr(op1, op2):
    op1_compare = op1
    op2_compare = op2
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = CastExpr(op1, Int[int(op1.dtype) + 1])
    if signed and typeof(op2.dtype, Uint):
        op2_compare = CastExpr(op2, Int[int(op2.dtype) + 1])

    cond = BinOpExpr((op1_compare, op2_compare), '>')
    return ConditionalExpr(cond=cond, operands=(op1, op2))


def parse_func_call(node, func_args, module_data):
    if hasattr(node.func, 'attr'):
        if node.func.attr == 'dtype':
            func = eval_expression(node.func, module_data.hdl_locals)
            try:
                ret = eval(f'func({", ".join(func_args)})')
                return ResExpr(ret)
            except TypeError:
                assert len(func_args) == 1
                return CastExpr(operand=func_args[0], cast_to=func)

        if node.func.attr == 'tout':
            return cast_return(func_args, module_data.out_ports)

    kwds = {}
    pg_types = registry('gear/type_arith')

    if hasattr(node.func, 'attr'):
        kwds['value'] = find_data_expression(node.func.value, module_data)
        func = node.func.attr
    elif hasattr(node.func, 'id'):
        func = node.func.id
    else:
        res = eval_expression(node.func, module_data.local_namespace)

        if is_type(res):
            return CastExpr(operand=func_args[0], cast_to=res)

        raise VisitError('Unrecognized func node in call')

    if func in pg_types:
        return CastExpr(operand=func_args[0],
                        cast_to=pg_types['cast'](func_args[0].dtype,
                                                 pg_types[func]))

    if f'call_{func}' in globals():
        return globals()[f'call_{func}'](*func_args, **kwds)

    if func in module_data.functions:
        # if function inlining
        func_code = module_data.functions[func]

        arg_unpacked = []
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                var = get_context_var(arg.value.id, module_data)

                if not isinstance(var, ConcatExpr):
                    raise VisitError(
                        f'Cannot unpack variable "{arg.value.id}"')

                for i in range(len(var.operands)):
                    arg_unpacked.append(
                        ast.fix_missing_locations(
                            ast.Subscript(value=arg.value,
                                          slice=ast.Index(value=ast.Num(i)),
                                          ctx=ast.Load)))
            else:
                arg_unpacked.append(arg)

        if func_code.__name__ != '<lambda>':
            func_ast = parse_function(func_code, module_data)
            func_ast.name = func
            func_params = func_ast.args.args

            if len(func_params) != len(func_args):
                raise VisitError(
                    f'Wrong number of arguments when calling function "{func}"'
                )

            for param, arg in zip(func_params, func_args):
                param.annotation = repr(arg.dtype)

            module_data.hdl_functions[func] = parse_ast(
                func_ast, module_data)

            return FunctionCall(
                operands=func_args,
                ret_dtype=module_data.hdl_functions[func].ret_dtype,
                name=func)

        else:
            var_name = f'{func}_res'
            module_data.variables[var_name] = None

            res = inline_function(func_code,
                                  arg_unpacked, {},
                                  module_data,
                                  returns=[var_name])

            module_data.add_variable(var_name, res[0].dtype)

            module_data.current_block.stmts.extend(res)

            return OperandVal(op=module_data.variables[var_name], context='v')

    # TODO : which params are actually needed? Maybe they are already passed
    # if func in self.ast_v.gear.params:
    #     assert isinstance(self.ast_v.gear.params[func], TypingMeta)
    #     assert len(func_args) == 1, 'Cast with multiple arguments'
    #     return CastExpr(
    #         operand=func_args[0], cast_to=self.ast_v.gear.params[func])

    # safe guard
    raise VisitError('Unrecognized func in call')


def call_len(arg, **kwds):
    return ResExpr(len(arg.dtype))


def call_print(arg, **kwds):
    pass


def call_int(arg, **kwds):
    # ignore cast
    return arg


def call_range(*arg, **kwds):
    if len(arg) == 1:
        start = ResExpr(arg[0].dtype(0))
        stop = arg[0]
        step = ast.Num(1)
    else:
        start = arg[0]
        stop = arg[1]
        step = ast.Num(1) if len(arg) == 2 else arg[2]

    return start, stop, step


def call_qrange(*arg, **kwds):
    return call_range(*arg)


def call_all(arg, **kwds):
    return ArrayOpExpr(arg, '&')


def call_max(*arg, **kwds):
    if len(arg) != 1:
        return reduce(max_expr, arg)

    arg = arg[0]

    assert isinstance(arg.op, IntfDef), 'Not supported yet...'
    assert typeof(arg.dtype, Tuple), 'Not supported yet...'

    op = []
    for field in arg.dtype.fields:
        op.append(AttrExpr(arg.op, [field]))

    return reduce(max_expr, op)


def call_enumerate(arg, **kwds):
    return ResExpr(len(arg)), arg


def call_sub(*arg, **kwds):
    assert not arg, 'Sub should be called without arguments'
    value = kwds['value']
    return CastExpr(value, cast_to=value.dtype.sub())


def call_get(*args, **kwds):
    return kwds['value']


def call_get_nb(*args, **kwds):
    return kwds['value']


def call_clk(*arg, **kwds):
    return None


def call_empty(*arg, **kwds):
    assert not arg, 'Empty should be called without arguments'
    value = kwds['value']
    expr = IntfDef(intf=value.intf, _name=value.name, context='valid')
    return UnaryOpExpr(expr, '!')


def call_gather(*arg, **kwds):
    return ConcatExpr(operands=list(arg))
