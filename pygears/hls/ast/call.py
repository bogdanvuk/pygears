import ast
import sys
import inspect
import math
from functools import partial
from . import Context, FuncContext, ir, node_visitor, visit_ast
from .inline import form_gear_args, call_gear, parse_func_call
from .cast import resolve_cast_func
from pygears import reg

from pygears.core.partial import Partial, MultiAlternativeError

from pygears.typing import code, div
from pygears.typing import is_type, typeof, Tuple, Array
from pygears.typing import cast, floor
from pygears.typing.queue import QueueMeta

from pygears.core.gear_inst import gear_signature, infer_params, get_function_context_dict, TypeMatchError, TooManyArguments, GearArgsNotSpecified


def parse_func_args(args, kwds, ctx):
    if args is None:
        args = []

    if kwds is None:
        kwds = []

    func_args = []
    for arg in args:
        if isinstance(arg, ast.Starred):
            var = visit_ast(arg.value, ctx)

            if isinstance(var, ir.ResExpr) and isinstance(var.val, list):
                func_args.extend(var.val)
            else:
                for i in range(len(var.dtype)):
                    func_args.append(ir.SubscriptExpr(val=var, index=ir.ResExpr(i)))

        else:
            func_args.append(visit_ast(arg, ctx))

    func_kwds = {kwd.arg: visit_ast(kwd.value, ctx) for kwd in kwds}

    return func_args, func_kwds


def get_gear_signatures(func, args, kwds):
    alternatives = [func] + getattr(func, 'alternatives', [])

    signatures = []
    kwds = {n: v.val if isinstance(v, ir.ResExpr) else v for n, v in kwds.items()}

    for f in alternatives:
        try:
            args_dict, templates = gear_signature(f, args, kwds)
        except (TooManyArguments, GearArgsNotSpecified):
            pass
        else:
            signatures.append((f, args_dict, templates))

    return signatures


def const_func_args(args, kwds):
    return (all(isinstance(node, ir.ResExpr) for node in args)
            and all(isinstance(node, ir.ResExpr) for node in kwds.values()))


def resolve_compile_time(func, args, kwds):
    # If all arguments are resolved expressions, maybe we can evaluate the
    # function at compile time
    return ir.ResExpr(func(*(a.val for a in args), **{n: v.val for n, v in kwds.items()}))


def resolve_gear_alternative(func, args, kwds):
    errors = []
    for f, args, templates in get_gear_signatures(func, args, kwds):
        try:
            params = infer_params(args, templates, get_function_context_dict(f))
        except TypeMatchError:
            errors.append((f, *sys.exc_info()))
        else:
            return (f, params)

    raise MultiAlternativeError(errors)


def resolve_gear_call(func, args, kwds):
    args, kwds = form_gear_args(args, kwds, func)

    f, params = resolve_gear_alternative(func, args, kwds)

    return ir.CallExpr(f, args, kwds, params)


compile_time_builtins = {
    all, max, int, len, type, isinstance, div, floor, cast, QueueMeta.sub, Array.code, Tuple.code,
    code, is_type, typeof
}


class Super:
    def __init__(self, cls, val):
        self.cls = cls
        self.val = val

    def __getattribute__(self, name):
        cls = super().__getattribute__('cls')
        val = super().__getattribute__('val')
        for base in inspect.getmro(cls):
            if name in base.__dict__:
                if base is object:
                    return getattr(base, name)

                f = base.__dict__[name]
                f = partial(f, val)

                return f
        else:
            raise AttributeError(name)


def get_class_that_defined_method(meth):
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing

    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls

    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


special_funcs = {
    abs: '__abs__',
    math.ceil: '__ceil__',
    math.floor: '__floor__',
    round: '__round__',
}


def hashable(v):
    """Determine whether `v` can be hashed."""
    try:
        hash(v)
    except TypeError:
        return False
    return True


def resolve_func(func, args, kwds, ctx):
    if is_type(func):
        if const_func_args(args, kwds):
            return resolve_compile_time(func, args, kwds)

        return resolve_cast_func(args[0], func)

    hashable_func = hashable(func)

    if isinstance(func, partial):
        args = func.args + tuple(args)
        func = func.func
    elif not inspect.isbuiltin(func) and hasattr(func, '__self__'):
        if func is super:
            if not isinstance(ctx, FuncContext):
                raise Exception(f'super() called outside a method function')

            f = ctx.funcref.func
            obj = ctx.ref('self')
            cls = get_class_that_defined_method(f).__base__

            return ir.ResExpr(Super(cls, obj))
        elif getattr(func, '__func__', None) in reg['hls/ir_builtins']:
            val = func.__self__
            for name, v in ctx.scope.items():
                if isinstance(v, ir.Variable) and val is v.val:
                    val = ctx.ref(name)
                    break

            return reg['hls/ir_builtins'][func.__func__](val, *args, **kwds)
        elif const_func_args(args, kwds):
            return resolve_compile_time(func, args, kwds)
        elif is_type(func.__self__):
            if func.__name__ == 'decode':
                return ir.CastExpr(args[0], ir.ResExpr(func.__self__))
            else:
                breakpoint()
                raise Exception
        else:
            breakpoint()
            func = func.__func__
            # raise Exception

    if hashable_func and func not in reg['hls/ir_builtins']:
        if func in special_funcs:
            return resolve_func(getattr(args[0].dtype, special_funcs[func]), args, kwds, ctx)

    if isinstance(func, Partial):
        intf, stmts = call_gear(func, *form_gear_args(args, kwds, func), ctx)
        ctx.ir_parent_block.stmts.extend(stmts)
        return intf

    if hashable_func and func in compile_time_builtins and const_func_args(args, kwds):
        return resolve_compile_time(func, args, kwds)

    if hashable_func and func in reg['hls/ir_builtins']:
        try:
            return reg['hls/ir_builtins'][func](*args, **kwds)
        except TypeError as e:
            breakpoint()
            raise SyntaxError(str(e).replace('<lambda>()', repr(func)))

    if const_func_args(args, kwds):
        return resolve_compile_time(func, args, kwds)
    elif hasattr(func, 'dispatch'):
        return resolve_func(func.dispatch(args[0].dtype), args, kwds, ctx)
    else:
        return parse_func_call(func, args, kwds, ctx)


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, (ir.ResExpr, ir.AttrExpr))

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    if not isinstance(name, ir.ResExpr):
        return ir.CallExpr(name, args, kwds)

    func = name.val

    return resolve_func(func, args, kwds, ctx)
