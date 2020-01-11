import ast
import typing
from functools import singledispatch
from dataclasses import dataclass, field
from .. import nodes

from pygears import config
from pygears.core.port import InPort, OutPort

from .utils import add_to_list

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


@dataclass
class Context:
    gear: typing.Any
    pydl_block_closure: typing.List = field(default_factory=list)
    submodules: typing.List[Submodule] = field(default_factory=list)
    scope: typing.Dict = field(default_factory=dict)
    local_namespace: typing.Dict = None

    def __post_init__(self):
        self.local_namespace = get_function_context_dict(self.gear.func)

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

    def ref(self, name, ctx='load'):
        return nodes.Name(name, self.scope[name], ctx=ctx)

    @property
    def pydl_parent_block(self):
        return self.pydl_block_closure[-1]


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

    pydl_node.stmts = [s for s in pydl_node.stmts if not isinstance(s, nodes.Expr)]

    ctx.pydl_block_closure.pop()

    return pydl_node
