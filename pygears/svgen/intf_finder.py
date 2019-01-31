import ast
import inspect
import re

import hdl_types as ht


def find_vararg_input(gear):
    sig = inspect.signature(gear.params['definition'].func)
    positional = [
        k for k, v in sig.parameters.items()
        if v.kind is inspect.Parameter.VAR_POSITIONAL
    ]

    res = {}
    for p in positional:
        args = []
        for port in gear.in_ports:
            if re.match(f'^{p}\d+$', port.basename):
                args.append(port)
        res[p] = tuple(args)

    return res


class IntfFinder(ast.NodeVisitor):
    def __init__(self, gear):
        self.regs = {}
        self.variables = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        }
        self.varargs = find_vararg_input(gear)
        self.intfs = {}
        self.intfs['varargs'] = self.varargs
        self.intfs['vars'] = {}

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
