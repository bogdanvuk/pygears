import ast
import inspect
import typing
from pygears.core.infer_ftypes import infer_ftypes
from pygears.typing import Any
from functools import singledispatch
from dataclasses import dataclass, field
from .. import ir

from pygears import config, Intf
from pygears.core.port import InPort, OutPort

from .utils import add_to_list, get_function_source, get_function_ast

from pygears.core.util import get_function_context_dict
from pygears.conf.trace import gear_definition_location
from jinja2.debug import make_traceback, TemplateSyntaxError, reraise
import sys


class SyntaxError(TemplateSyntaxError):
    pass


@dataclass
class Submodule:
    gear: typing.Any
    in_ports: typing.List[ir.Interface]
    out_ports: typing.List[ir.Interface]


class Function:
    def __init__(self, func, args, kwds, uniqueid=None):
        self.source = get_function_source(func)
        self.func = func
        self.ast = get_function_ast(func)
        self.basename = ''.join(e for e in func.__name__ if e.isalnum())
        self.uniqueid = uniqueid
        # TODO: Include keywords here
        self._hash = hash(self.source) ^ hash(tuple(arg.dtype for arg in args))

    @property
    def name(self):
        if self.uniqueid is None:
            return self.basename

        return f'{self.basename}_{self.uniqueid}'

    def __hash__(self):
        return self._hash


class Context:
    def __init__(self):
        self.scope: typing.Dict = {}
        self.args = {}
        self.local_namespace: typing.Dict = None
        self.functions: typing.Mapping[Function, FuncContext] = {}
        self.pydl_block_closure: typing.List = []
        self.submodules: typing.List[Submodule] = []

    def ref(self, name, ctx='load'):
        return ir.Name(name, self.scope[name], ctx=ctx)

    def find_unique_name(self, name):
        res_name = name
        i = 0
        while res_name in self.scope:
            i += 1
            res_name = f'{name}_{i}'

        return res_name

    @property
    def pydl_parent_block(self):
        return self.pydl_block_closure[-1]

    @property
    def intfs(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, ir.Variable) and isinstance(obj.val, Intf)
        }

    @property
    def regs(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, ir.Variable) and obj.reg
        }

    @property
    def variables(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, ir.Variable) and obj.val is None
        }


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
        self.local_namespace = get_function_context_dict(self.gear.func)

        paramspec = inspect.getfullargspec(self.gear.func)

        vararg = []
        for p in self.gear.in_ports:
            self.scope[p.basename] = ir.Variable(p.basename, val=p.consumer)

            if paramspec.varargs and p.basename.startswith(paramspec.varargs):
                vararg.append(self.ref(p.basename))

        if paramspec.varargs:
            self.local_namespace[paramspec.varargs] = ir.ConcatExpr(vararg)
            # self.scope[paramspec.varargs] = ir.Variable(p.basename, val=p.consumer)
            # self.scope[paramspec.varargs] = ir.Variable(paramspec.varargs, ir.ConcatExpr(vararg))

        for p in self.gear.out_ports:
            # self.scope[p.basename] = ir.Interface(p.producer, 'out')
            self.scope[p.basename] = ir.Variable(p.basename, val=p.producer)
            # p.producer.name = p.basename
            # self.scope[p.basename] = ir.ResExpr(IntfProxy(p))

        for k, v in self.gear.explicit_params.items():
            self.scope[k] = ir.ResExpr(v)

    @property
    def in_ports(self):
        return [
            obj for obj in self.scope.values() if (
                isinstance(obj, ir.Interface) and isinstance(obj.intf, Intf)
                and obj.intf.producer and obj.intf.producer.gear is self.gear)
        ]

    @property
    def out_ports(self):
        return [self.ref(p.basename) for p in self.gear.out_ports]

        # return [
        #     obj for obj in self.scope.values()
        #     if (isinstance(obj, ir.Interface) and isinstance(obj.intf, Intf)
        #         and len(obj.intf.consumers) == 1
        #         and obj.intf.consumers[0].gear is self.gear)
        # ]


class FuncContext(Context):
    def __init__(self, funcref: Function, args, kwds):
        super().__init__()
        self.funcref = funcref
        func = funcref.func

        self.local_namespace = get_function_context_dict(func)

        paramspec = inspect.getfullargspec(funcref.func)
        self.args = dict(zip(paramspec.args, args))
        self.args.update(kwds)
        self.ret_dtype = None
        self.const_args = {}

        if func.__annotations__:
            kwddefaults = paramspec.kwonlydefaults or {}
            params = {**func.__annotations__, **kwddefaults}

            for a in paramspec.args:
                if a not in params:
                    params[a] = Any

            arg_types = {
                name: self.args[name].dtype
                for name in paramspec.args if name in self.args
            }

            for name, var in self.args.items():
                if name in params:
                    continue

                if isinstance(var, ir.ResExpr):
                    params[name] = var.val
                else:
                    params[name] = var

            res = infer_ftypes(
                params=params, args=arg_types, namespace=self.local_namespace)

            for name, dtype in res.items():
                if name == 'return':
                    continue

                if isinstance(self.args[name], ir.ResExpr):
                    self.local_namespace[name] = self.args[name].val
                    self.const_args[name] = self.args[name]
                else:
                    self.scope[name] = ir.Variable(name, dtype)
        else:
            for name, arg in self.args.items():
                if isinstance(arg, ir.ResExpr):
                    self.local_namespace[name] = arg.val
                    self.const_args[name] = arg
                else:
                    self.scope[name] = ir.Variable(name, arg.dtype)

        for name in self.const_args:
            del self.args[name]


def node_visitor(ast_type):
    def wrapper(f):
        def func_wrapper(node, ctx):
            if config['trace/level'] == 0:
                return f(node, ctx)

            try:
                return f(node, ctx)
            except SyntaxError:
                ttype, value, traceback = sys.exc_info()
                raise value.with_traceback(traceback)
            except Exception as e:
                func, fn, ln = gear_definition_location(ctx.gear.func)
                msg = (
                    f'{str(e)}\n    - when compiling gear "{ctx.gear.name}" with'
                    f' parameters {ctx.gear.params}')

                err = SyntaxError(msg, ln + node.lineno - 1, filename=fn)

                traceback = make_traceback((SyntaxError, err, sys.exc_info()[2]))
                exc_type, exc_value, tb = traceback.standard_exc_info

            reraise(exc_type, exc_value, tb)

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

    # for _, value in ast.iter_fields(node):
    #     if isinstance(value, list):
    #         for item in value:
    #             if isinstance(item, ast.AST):
    #                 visit_ast(item, ctx)
    #     elif isinstance(value, ast.AST):
    #         visit_ast(value, ctx)


def visit_block(pydl_node, body, ctx):
    ctx.pydl_block_closure.append(pydl_node)
    for stmt in body:
        res_stmt = visit_ast(stmt, ctx)
        add_to_list(pydl_node.stmts, res_stmt)

    # Remove expressions that are added as block statements
    stmts = pydl_node.stmts
    pydl_node.stmts = []
    for s in stmts:
        if isinstance(s, ir.CallExpr):
            pydl_node.stmts.append(ir.ExprStatement(s))
        elif isinstance(s, ir.Expr):
            pass
            # print("Expression as statement!")
            # print(s)
        else:
            pydl_node.stmts.append(s)

    ctx.pydl_block_closure.pop()

    return pydl_node
