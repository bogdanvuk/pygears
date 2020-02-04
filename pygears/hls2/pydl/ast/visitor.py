import ast
import inspect
import typing
from pygears.core.infer_ftypes import infer_ftypes
from pygears.typing import Any
from functools import singledispatch
from dataclasses import dataclass, field
from .. import nodes

from pygears import config
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
    in_ports: typing.List[nodes.Interface]
    out_ports: typing.List[nodes.Interface]


class Function:
    def __init__(self, func, args, kwds, uniqueid=None):
        self.source = get_function_source(func)
        self.func = func
        self.ast = get_function_ast(func)
        self.basename = func.__name__
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
        return nodes.Name(name, self.scope[name], ctx=ctx)

    def find_unique_name(self, name):
        res_name = name
        i = 0
        while res_name in self.scope:
            i += 1
            res_name = f'{name}_i'

        return res_name

    @property
    def pydl_parent_block(self):
        return self.pydl_block_closure[-1]

    @property
    def intfs(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, nodes.Interface)
        }

    @property
    def variables(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, nodes.Variable)
        }

    @property
    def regs(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, nodes.Register)
        }

    @property
    def variables(self):
        return {
            name: obj
            for name, obj in self.scope.items()
            if isinstance(obj, nodes.Variable) and name not in self.args
        }


class GearContext(Context):
    def __init__(self, gear):
        super().__init__()
        self.gear = gear
        self.local_namespace = get_function_context_dict(self.gear.func)

        paramspec = inspect.getfullargspec(self.gear.func)

        vararg = []
        for p in self.gear.in_ports:
            if paramspec.varargs and p.basename.startswith(paramspec.varargs):
                vararg.append(nodes.Interface(p, 'in'))

            self.scope[p.basename] = nodes.Interface(p, 'in')

        if paramspec.varargs:
            self.local_namespace[paramspec.varargs] = nodes.ResExpr(vararg)
            # self.scope[paramspec.varargs] = nodes.ConcatExpr(vararg)

        for p in self.gear.out_ports:
            self.scope[p.basename] = nodes.Interface(p, 'out')

        for k, v in self.gear.explicit_params.items():
            self.scope[k] = nodes.ResExpr(v)

    @property
    def in_ports(self):
        return [
            obj for obj in self.scope.values()
            if (isinstance(obj, nodes.Interface) and isinstance(
                obj.intf, InPort) and obj.intf.gear is self.gear)
        ]

    @property
    def out_ports(self):
        return [
            obj for obj in self.scope.values()
            if (isinstance(obj, nodes.Interface) and isinstance(
                obj.intf, OutPort) and obj.intf.gear is self.gear)
        ]


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
                for name in params if name in self.args
            }

            for name, var in self.args.items():
                if name in params:
                    continue

                if isinstance(var, nodes.ResExpr):
                    params[name] = var.val
                else:
                    params[name] = var

            res = infer_ftypes(params=params,
                               args=arg_types,
                               namespace=self.local_namespace)

            for name, dtype in res.items():
                if name == 'return':
                    continue

                if isinstance(self.args[name], nodes.ResExpr):
                    self.local_namespace[name] = self.args[name].val
                    self.const_args[name] = self.args[name]
                else:
                    self.scope[name] = nodes.Variable(name, dtype)
        else:
            for name, arg in self.args.items():
                if isinstance(arg, nodes.ResExpr):
                    self.local_namespace[name] = arg.val
                    self.const_args[name] = arg
                else:
                    self.scope[name] = nodes.Variable(name, arg.dtype)

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
                err = SyntaxError(str(e), ln + node.lineno - 1, filename=fn)

                traceback = make_traceback(
                    (SyntaxError, err, sys.exc_info()[2]))
                exc_type, exc_value, tb = traceback.standard_exc_info

            reraise(exc_type, exc_value, tb)

        return visit_ast.register(ast_type)(func_wrapper)

    return wrapper


@singledispatch
def visit_ast(node, ctx):
    """Used by default. Called if no explicit function exists for a node."""
    if node is None:
        return nodes.ResExpr(None)

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

    for s in pydl_node.stmts:
        if isinstance(s, nodes.Expr):
            print("Expression as statement!")
            print(s)

    # Remove expressions that are added as block statements
    pydl_node.stmts = [
        s for s in pydl_node.stmts if not isinstance(s, nodes.Expr)
    ]

    ctx.pydl_block_closure.pop()

    return pydl_node
