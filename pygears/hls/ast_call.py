import ast
from functools import reduce

from pygears.typing import Int, Tuple, Uint, Unit, is_type, typeof

from .ast_parse import parse_ast
from .hls_expressions import (ArrayOpExpr, AttrExpr, BinOpExpr, CastExpr,
                              ConditionalExpr, IntfDef, ResExpr, UnaryOpExpr)
from .utils import (VisitError, cast_return, eval_expression,
                    find_data_expression)


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
        return call_func(node, func_args, module_data)


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


def call_func(node, func_args, module_data):
    if hasattr(node.func, 'attr'):
        if node.func.attr == 'dtype':
            func = eval_expression(node.func, module_data.hdl_locals)
            ret = eval(f'func({", ".join(func_args)})')
            return ResExpr(ret)

        if node.func.attr == 'tout':
            return cast_return(func_args, module_data.out_ports)

    kwds = {}
    if hasattr(node.func, 'attr'):
        kwds['value'] = find_data_expression(node.func.value, module_data)
        func = node.func.attr
    elif hasattr(node.func, 'id'):
        func = node.func.id
    else:
        # safe guard
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
