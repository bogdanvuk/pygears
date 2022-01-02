import inspect
import typing
from pygears.core.infer_ftypes import infer_ftypes
from pygears.core.gear import OutSig, InSig
from pygears.typing import Any, typeof
from functools import singledispatch
from dataclasses import dataclass
from .. import ir

from pygears import reg, Intf

from .utils import add_to_list, get_function_source, get_function_ast

from pygears.core.util import get_function_context_dict
from pygears.conf.trace import gear_definition_location
from pygears.conf.trace import make_traceback, TraceException
import sys


class HLSSyntaxError(TraceException):
    pass


def form_hls_syntax_error(ctx, e, lineno=1):
    msg = str(e)
    for c in reversed(reg['hls/ctx']):
        if isinstance(c, GearContext):
            func, fn, ln, _ = gear_definition_location(c.gear.func)
            msg += (f'\n    - when compiling gear "{c.gear.name}" with'
                    f' parameters {c.gear.params}')
        else:
            func, fn, ln, _ = gear_definition_location(c.funcref.func)
            msg += (f'\n    - when compiling function "{c.funcref.func}" with'
                    f' signature {c.signature}')

    err = HLSSyntaxError(msg, ln + lineno - 1, filename=fn)

    traceback = make_traceback((HLSSyntaxError, err, sys.exc_info()[2]))
    _, exc_value, tb = traceback.standard_exc_info

    return exc_value, tb


@dataclass
class Submodule:
    gear: typing.Any
    in_ports: typing.List
    out_ports: typing.List


def hashable(v):
    """Determine whether `v` can be hashed."""
    try:
        hash(v)
    except TypeError:
        return False
    return True


class Function:
    def __init__(self, func, args, kwds, uniqueid=None):
        self.source = get_function_source(func)
        self.func = func
        self.ast = get_function_ast(func)
        self.basename = ''.join(e for e in func.__name__ if e.isalnum() or e == '_')
        self.uniqueid = uniqueid

        # If there were some constant arguments, their values were embeded into
        # funtion code, so we need to take values as part of the hash.
        hargs = tuple(arg.val if isinstance(arg, ir.ResExpr) else arg.dtype for arg in args)

        hkwds = tuple((k, v) for k, v in kwds.items() if hashable(v))

        if self.source:
            # TODO: Include keywords here
            self._hash = hash(self.source) ^ hash(hargs) ^ hash(hkwds)
        else:
            self._hash = hash(self.__qualname__) ^ hash(hargs) ^ hash(hkwds)

    @property
    def name(self):
        if self.uniqueid is None:
            return self.basename

        return f'{self.basename}_{self.uniqueid}'

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return self._hash


class Context:
    def __init__(self):
        self.scope: typing.Dict = {}
        self.methods = {}
        self.closures = []
        self.closure_alias_maps = {}
        self.expr_closure = None
        self.local_namespace: typing.Dict = {'__builtins__': __builtins__}
        self.ir_block_closure: typing.List = []
        self.submodules: typing.List[Submodule] = []
        self.reaching: typing.Dict = {}
        self.ast_stmt_map: typing.Dict = {}
        self.reaching = {}
        self.registers = {}

    def ref(self, name, ctx='load'):
        if name in self.scope:
            return ir.Name(name, self.scope[name], ctx=ctx)

        if name in self.local_namespace:
            return ir.ResExpr(self.local_namespace[name])

        raise KeyError

    def find_unique_name(self, name):
        res_name = name
        i = 0
        while res_name in self.scope:
            i += 1
            res_name = f'{name}_{i}'

        return res_name

    def new_closure(self, node):
        if self.closures:
            scope = self.alias_map.copy()
        else:
            scope = self.local_namespace.copy()

        self.closure_alias_maps[node] = scope
        self.closures.append(node)

    @property
    def alias_map(self):
        if self.closures:
            return self.closure_alias_maps[self.ir_parent_block]
        else:
            return {}

    @property
    def ir_parent_block(self):
        return self.closures[-1]

    @property
    def variables(self):
        return {
            name: obj
            for name, obj in self.scope.items() if isinstance(obj, ir.Variable) and obj.reg is False
        }

    @property
    def regs(self):
        return {}


class IntfProxy(Intf):
    def __init__(self, port):
        self.port = port

    @property
    def dtype(self):
        return self.port.dtype

    def __str__(self):
        return self.port.basename

    def __repr__(self):
        return repr(self.port)


class GearContext(Context):
    def __init__(self, gear):
        super().__init__()
        self.gear = gear
        self.functions: typing.Mapping[Function, FuncContext] = {}
        self.local_namespace = get_function_context_dict(self.gear.func).copy()

        paramspec = inspect.getfullargspec(self.gear.func)

        # TODO: If local variable shadows output interface name, they will clash!!! (Example: dout)
        vararg = []
        for p in self.gear.in_ports:
            self.scope[p.basename] = ir.Variable(p.basename, ir.IntfType[p.dtype, ir.IntfType.iin])

            if paramspec.varargs and p.basename.startswith(paramspec.varargs):
                vararg.append(self.ref(p.basename))

        if paramspec.varargs:
            self.local_namespace[paramspec.varargs] = ir.ConcatExpr(vararg)

        for p in self.gear.out_ports:
            self.scope[f'{p.basename}'] = ir.Variable(
                f'{p.basename}', ir.IntfType[p.consumer.dtype, ir.IntfType.iout])

        for k, v in self.gear.explicit_params.items():
            self.local_namespace[k] = ir.ResExpr(v)

    @property
    def intfs(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, ir.Variable) and typeof(obj.dtype, ir.IntfType)
        }

    @property
    def signals(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, ir.Variable) and isinstance(obj.val, (OutSig, InSig))
        }

    @property
    def regs(self):
        return {
            name: obj
            for name, obj in self.scope.items() if isinstance(obj, ir.Variable) and obj.reg
        }

    @property
    def in_ports(self):
        return [
            obj for obj in self.scope.values()
            if (isinstance(obj, ir.Interface) and isinstance(obj.intf, Intf) and obj.intf.producer
                and obj.intf.producer.gear is self.gear)
        ]

    @property
    def out_ports(self):
        return [self.ref(f'{p.basename}') for p in self.gear.out_ports]


class FuncContext(Context):
    def argdict(self, args, kwds):
        paramspec = inspect.getfullargspec(self.funcref.func)
        args = dict(zip(paramspec.args, args))
        args.update(kwds)

        for name in self.const_args:
            if name not in args:
                continue

            del args[name]

        return args

    def __init__(self, funcref: Function, args, kwds):
        super().__init__()
        self.funcref = funcref

        func = funcref.func

        # self.name = funcref.name
        self.local_namespace = get_function_context_dict(func).copy()

        paramspec = inspect.getfullargspec(funcref.func)
        args = dict(zip(paramspec.args, args))
        args.update(kwds)

        self.ret_dtype = None
        self.const_args = {}

        kwddefaults = paramspec.kwonlydefaults or {}

        if paramspec.defaults:
            for name, val in zip(reversed(paramspec.args), reversed(paramspec.defaults)):
                if name in args:
                    continue

                args[name] = ir.ResExpr(val)

        for k, v in kwddefaults.items():
            if k not in args:
                args[k] = ir.ResExpr(v)

        if func.__annotations__:
            params = {**func.__annotations__, **kwddefaults}

            for a in paramspec.args:
                if a not in params:
                    params[a] = Any

            arg_types = {}
            for name in paramspec.args:
                if name not in args:
                    continue

                arg_types[name] = args[name].dtype

            for name, var in args.items():
                if name in params:
                    continue

                if isinstance(var, ir.ResExpr):
                    params[name] = var.val
                else:
                    params[name] = var

            for n, v in kwds.items():
                if isinstance(v, ir.ResExpr):
                    params[n] = v.val

            res = infer_ftypes(params=params, args=arg_types, namespace=self.local_namespace)

            if 'return' in res:
                self.ret_dtype = res['return']

            for name, dtype in res.items():
                if name not in args:
                    continue

                if isinstance(args[name], ir.ResExpr):
                    self.local_namespace[name] = args[name].val
                    self.const_args[name] = args[name]
                else:
                    self.scope[name] = ir.Variable(name, dtype)
        else:
            for name, arg in args.items():
                if isinstance(arg, ir.ResExpr):
                    self.local_namespace[name] = arg.val
                    self.const_args[name] = arg
                else:
                    self.scope[name] = ir.Variable(name, arg.dtype)

        # self.scope maybe contains infered type, so use that if present
        self.signature = {
            name: self.scope.get(name, var).dtype
            for name, var in args.items() if name not in self.const_args
        }


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


def node_visitor(ast_type):
    def wrapper(f):
        def func_wrapper(node, ctx):
            if reg['trace/level'] == 0:
                return f(node, ctx)

            err = None

            try:
                return f(node, ctx)
            except Exception as e:
                if isinstance(e, HLSSyntaxError) and e.lineno is not None:
                    _, exc_value, tb = sys.exc_info()
                elif hasattr(node, 'lineno'):
                    exc_value, tb = form_hls_syntax_error(ctx, e, node.lineno)
                else:
                    err = e
                    tb = None

            if err is not None:
                raise err
            else:
                raise exc_value.with_traceback(tb)

        if isinstance(ast_type, tuple):
            f_ret = visit_ast.register(ast_type[0])(func_wrapper)
            for t in ast_type[1:]:
                f_ret = visit_ast.register(t)(f_ret)
        else:
            f_ret = visit_ast.register(ast_type)(func_wrapper)

        return f_ret

    return wrapper


@singledispatch
def visit_ast(node, ctx):
    """Used by default. Called if no explicit function exists for a node."""
    if node is None:
        return ir.ResExpr(None)

    breakpoint()
    raise SyntaxError(f"Unsupported language construct", node.lineno)


def visit_block(ir_node, body, ctx):
    ctx.new_closure(ir_node)
    for stmt in body:
        res_stmt = visit_ast(stmt, ctx)
        if not isinstance(res_stmt, list):
            res_stmt = [res_stmt]

        for s in res_stmt:
            if s is None:
                continue

            ir_node.stmts.append(s)
            if isinstance(ir_node, ir.FuncBlock) and isinstance(s, ir.FuncReturn):
                # No need to continue, return has been hit
                break

        if ir_node.stmts and isinstance(ir_node, ir.FuncBlock) and isinstance(
                ir_node.stmts[-1], ir.FuncReturn):
            # No need to continue, return has been hit
            break

    # Remove expressions that are added as block statements
    stmts = ir_node.stmts
    ir_node.stmts = []
    for s in stmts:
        if isinstance(s, ir.CallExpr):
            ir_node.stmts.append(ir.ExprStatement(s))
        elif isinstance(s, ir.Expr):
            pass
        else:
            ir_node.stmts.append(s)

    ctx.closures.pop()

    return ir_node
