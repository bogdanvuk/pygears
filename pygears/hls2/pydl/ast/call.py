import ast
import inspect
from . import Context, SyntaxError, node_visitor, nodes, visit_ast, visit_block
from ..pydl_builtins import builtins
from pygears.core.partial import extract_arg_kwds, combine_arg_kwds
from pygears.typing import is_type


def parse_func_args(args, kwds, ctx):
    if args is None:
        args = []

    if kwds is None:
        kwds = []

    arg_unpacked = []
    for arg in args:
        if isinstance(arg, ast.Starred):
            breakpoint()
            # var = get_context_var(arg.value.id, ctx)

            # if not isinstance(var, ConcatExpr):
            #     raise VisitError(f'Cannot unpack variable "{arg.value.id}"')

            # for i in range(len(var.operands)):
            #     arg_unpacked.append(
            #         ast.fix_missing_locations(
            #             ast.Subscript(value=arg.value,
            #                           slice=ast.Index(value=ast.Num(i)),
            #                           ctx=ast.Load)))
        else:
            arg_unpacked.append(arg)

    func_args = [visit_ast(arg, ctx) for arg in arg_unpacked]

    func_kwds = {kwd.arg: visit_ast(kwd.value, ctx) for kwd in kwds}

    return func_args, func_kwds


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, nodes.ResExpr)

    func = name.val

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    kwd_args, kwds_only = extract_arg_kwds(kwds, func)
    args_only = combine_arg_kwds(args, kwd_args, func)

    # If all arguments are resolved expressions, maybe we can evaluate the
    # function at compile time
    if (all(isinstance(node, nodes.ResExpr) for node in args_only) and all(
            isinstance(node, nodes.ResExpr) for node in kwds_only.values())):
        return nodes.ResExpr(
            func(*(a.val for a in args_only),
                 **{n: v.val
                    for n, v in kwds_only.items()}))

    # If we are dealing with bound methods
    if not inspect.isbuiltin(func) and hasattr(func, '__self__'):
        raise Exception

    if func in builtins:
        func = builtins[func](*args_only, **kwds_only)
    elif is_type(func):
        raise Exception
        # from .hdl_cast import resolve_cast_func
        # func = resolve_cast_func(func_args[0], func)

    if isinstance(func, nodes.Expr):
        return func

    pass
