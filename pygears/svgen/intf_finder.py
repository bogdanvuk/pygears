import ast
import inspect
import re

import hdl_types as ht

from .hdl_ast import eval_expression


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
    for p in positional:
        args = []
        for port in gear.in_ports:
            if re.match(f'^{p}\d+$', port.basename):
                args.append(port)
        pos_in_ports[p] = tuple(args)

    named_in_ports = {
        p.basename: p.consumer
        for p in gear.in_ports if p.basename in named
    }

    return named_in_ports, pos_in_ports


class IntfFinder(ast.NodeVisitor):
    def __init__(self, gear):
        self.regs = {}
        self.variables = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        }
        self.out_names = [p.basename for p in gear.out_ports]
        self.namedargs, self.varargs = find_vararg_input(gear)
        self.intfs = {}
        self.intfs['namedargs'] = self.namedargs
        self.intfs['varargs'] = self.varargs
        self.intfs['vars'] = {}
        self.intfs['outputs'] = {}

    def visit_For(self, node):
        for arg in node.iter.args:
            if hasattr(arg, 'id') and arg.id in self.varargs:
                if isinstance(node.target, ast.Tuple):
                    self.intfs['vars'][node.target.elts[-1].id] = ht.IntfDef(
                        self.varargs[arg.id], node.target.elts[-1].id)
                else:
                    self.intfs['vars'][node.target.id] = ht.IntfDef(
                        self.varargs[arg.id], node.target.elts[-1].id)
                break

        for stmt in node.body:
            self.visit(stmt)

    def visit_Assign(self, node):
        if hasattr(node.targets[0], 'id'):
            name = node.targets[0].id
        elif hasattr(node.targets[0], 'value'):
            name = node.targets[0].value.id
        else:
            assert False, 'Unknown assignment type'

        if name not in self.intfs['outputs']:
            scope = {**self.local_params, **self.intfs['varargs']}
            try:
                val = eval_expression(node.value, scope)
            except NameError:
                return

            if val is None:
                self.intfs['outputs'][name] = self.out_names[0]
            elif isinstance(val,
                            (list, tuple)) and all([v is None for v in val]):
                self.intfs['outputs'][name] = self.out_names
