import ast
import inspect
import re

from .hls_expressions import IntfDef
from .utils import eval_expression, find_assign_target


def find_vararg_input(gear):
    sig = inspect.signature(gear.params['definition'].func)
    # *args in func definition
    positional = [
        k for k, v in sig.parameters.items()
        if v.kind is inspect.Parameter.VAR_POSITIONAL
    ]
    # **kwargs in func definition
    keyword = {
        k: None
        for k, v in sig.parameters.items() if v.kind in
        [inspect.Parameter.VAR_KEYWORD, inspect.Parameter.KEYWORD_ONLY]
    }
    # named parameters in func definition
    named = {
        k: None
        for k, v in sig.parameters.items()
        if (k not in positional) and (k not in keyword)
    }

    pos_in_ports = {}
    for pos in positional:
        args = []
        for port in gear.in_ports:
            if re.match(f'^{pos}\d+$', port.basename):
                args.append(port)
        pos_in_ports[pos] = tuple(args)

    named_in_ports = {
        p.basename: p.consumer
        for p in gear.in_ports if p.basename in named
    }

    return named_in_ports, pos_in_ports


class IntfFinder(ast.NodeVisitor):
    def __init__(self, module_data):
        self.module_data = module_data
        gear = module_data.gear

        self.namedargs, self.varargs = find_vararg_input(gear)

        self.module_data.local_namespace.update(self.namedargs)
        self.module_data.local_namespace.update(self.varargs)

        named = {}
        for port in self.module_data.in_ports:
            if port in self.namedargs:
                named[port] = self.module_data.in_ports[port]
        self.module_data.hdl_locals.update(named)
        self.module_data.hdl_locals.update(self.varargs)

        self.out_names = [p.basename for p in gear.out_ports]

    def _set_in_intf(self, name, arg_name=None, target_name=None):
        if arg_name is None:
            arg_name = name
        if target_name is None:
            target_name = name

        self.module_data.in_intfs[name] = IntfDef(
            intf=self.varargs[arg_name], _name=target_name)

    def visit_async(self, node, expr):
        if isinstance(expr, ast.Subscript):
            self._set_in_intf(expr.value.id)

        for stmt in node.body:
            self.visit(stmt)

    def visit_AsyncFor(self, node):
        self.visit_async(node, node.iter)

    def visit_AsyncWith(self, node):
        self.visit_async(node, node.items[0].context_expr)

    def visit_For(self, node):
        for arg in node.iter.args:
            if hasattr(arg, 'id') and arg.id in self.varargs:
                if isinstance(node.target, ast.Tuple):
                    name = node.target.elts[-1].id
                else:
                    name = node.target.id

                self._set_in_intf(name, arg.id, node.target.elts[-1].id)
                break

        for stmt in node.body:
            self.visit(stmt)

    def visit_Assign(self, node):
        names = find_assign_target(node)

        for name in names:
            if name not in self.out_names:
                try:
                    val = eval_expression(node.value,
                                          self.module_data.local_namespace)
                except NameError:
                    return

                if val is None:
                    self.module_data.out_intfs[name] = self.out_names[0]
                elif isinstance(val, (list, tuple)) and all(
                    [v is None for v in val]):
                    self.module_data.out_intfs[name] = self.out_names
