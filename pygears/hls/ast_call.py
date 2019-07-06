import ast
from functools import reduce

from pygears import registry
from pygears.typing import Int, Tuple, Uint, Unit, is_type, typeof
from pygears.core.util import is_standard_func

from .ast_parse import parse_ast
from .hls_expressions import (ArrayOpExpr, AttrExpr, BinOpExpr, CastExpr,
                              ConcatExpr, ConditionalExpr, IntfDef, ResExpr,
                              UnaryOpExpr)
from .utils import (VisitError, add_to_list, cast_return, eval_expression,
                    find_data_expression, find_target, set_pg_type,
                    get_function_source, get_context_var)


@parse_ast.register(ast.Call)
def parse_call(node, module_data):
    arg_nodes = [find_data_expression(arg, module_data) for arg in node.args]

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


def parse_functions(node, module_data, returns=None):
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

    curr_func = module_data.functions[node.func.id]
    if not is_standard_func(curr_func):
        raise VisitError(f'Only standard functions are supported!')

    source = get_function_source(curr_func)
    func_ast = ast.parse(source).body[0]

    replace_kwds = {n.arg: n.value.id for n in node.keywords}

    arguments = []
    for arg in node.args:
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

    AstFunctionReplace(argument_map, returns).visit(func_ast)
    func_ast = ast.fix_missing_locations(func_ast)

    res = []
    for stmt in func_ast.body:
        res_stmt = parse_ast(stmt, module_data)
        add_to_list(res, res_stmt)
    return res


class AstFunctionReplace(ast.NodeTransformer):
    def __init__(self, args, returns):
        self.args = args
        self.returns = returns

    def visit_Name(self, node):
        if node.id in self.args:
            switch_val = self.args[node.id]
            if not isinstance(switch_val, str):
                return switch_val
            node.id = switch_val

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
    if hasattr(node.func, 'attr'):
        kwds['value'] = find_data_expression(node.func.value, module_data)
        func = node.func.attr
    elif hasattr(node.func, 'id'):
        func = node.func.id
    else:
        try:
            pg_type = node.func.value.id
            width = node.func.slice.value.n
        except AttributeError:
            raise VisitError('Unrecognized func node in call')

        pg_types = registry('gear/type_arith')
        if pg_type in pg_types:
            assert len(
                func_args
            ) == 1, f'Type casting supported for simple types for now'
            return CastExpr(operand=func_args[0],
                            cast_to=pg_types[pg_type][width])

        raise VisitError('Unrecognized func node in call')

    if f'call_{func}' in globals():
        return globals()[f'call_{func}'](*func_args, **kwds)

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
