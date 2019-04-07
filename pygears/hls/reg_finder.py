import ast

from pygears.typing import Uint, bitw, is_type

from . import hdl_types as ht
from .hdl_utils import (eval_expression, find_assign_target, find_for_target,
                        hls_log, set_pg_type)


class AstAyncFinder(ast.NodeVisitor):
    def __init__(self):
        self.blocking = False

    def visit_Yield(self, node):
        self.blocking = True

    def visit_YieldFrom(self, node):
        self.blocking = True

    def visit_AsyncFor(self, node):
        self.blocking = True

    def visit_AsyncWith(self, node):
        self.blocking = True


def find_async(node):
    async_visit = AstAyncFinder()
    async_visit.visit(node)
    return async_visit.blocking


def find_comb_loop(node):
    comb_loop = False
    if hasattr(node, 'orelse'):
        try:
            val = node.orelse[0].value
            comb_loop = isinstance(val,
                                   ast.Await) and (val.value.func.id == 'clk')
        except (AttributeError, IndexError):
            pass

    return comb_loop


class RegFinder(ast.NodeVisitor):
    def __init__(self, gear, intfs):
        self.regs = {}
        self.variables = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params,
            **intfs['varargs']
        }
        self.intf_outs = intfs['outputs'].keys()
        nested = [list(val.keys()) for intf, val in intfs.items()]
        self.intfs = [item for sublist in nested for item in sublist]

    def promote_var_to_reg(self, name):
        val = self.variables[name]

        # wire, not register
        # TODO
        if not is_type(type(val)):
            return

        val = set_pg_type(val)

        self.regs[name] = ht.ResExpr(val)

    def clean_variables(self):
        for reg in self.regs:
            if reg in self.variables:
                del self.variables[reg]

    def visit_AugAssign(self, node):
        self.promote_var_to_reg(node.target.id)

    def visit_For(self, node):
        names = find_for_target(node)

        register_var = False
        if not find_comb_loop(node):
            register_var = find_async(node)

        for i, name in enumerate(names):
            if name in self.variables:
                self.promote_var_to_reg(name)
            else:
                if name not in self.intfs:
                    if i == 0:
                        try:
                            rng = eval_expression(node.iter, self.local_params)
                            length = len([v for v in rng])
                        except NameError:
                            length = 2**32 - 1

                        if register_var:
                            self.regs[name] = ht.ResExpr(Uint[bitw(length)](0))
                            hls_log().debug(
                                f'For loop iterator {name} registered with width {bitw(length)}'
                            )
                        else:
                            self.variables[name] = ht.ResExpr(
                                Uint[bitw(length)](0))
                            hls_log().debug(
                                f'For loop iterator {name} unrolled with width {bitw(length)}'
                            )
                    else:
                        hls_log().debug(
                            f'For loop iterator {name} not registered')

        for stmt in node.body:
            self.visit(stmt)

    def visit_Assign(self, node):
        names = find_assign_target(node)

        for name in names:
            if name in self.intf_outs:
                continue

            if name not in self.variables:
                try:
                    self.variables[name] = eval_expression(
                        node.value, self.local_params)
                except NameError:
                    # wires/variables are not defined previously
                    self.variables[name] = node.value
            else:
                self.promote_var_to_reg(name)
