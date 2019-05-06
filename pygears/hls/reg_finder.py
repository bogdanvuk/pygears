import ast

from pygears.typing import Uint, bitw, is_type

from .hls_expressions import ResExpr
from .utils import (eval_expression, find_assign_target, find_for_target,
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


def find_var_length(expr, params):
    try:
        rng = eval_expression(expr, params)
        return len([v for v in rng])
    except NameError:
        return 2**32 - 1


def find_comb_loop(node, reg_finder):
    comb_loop = False
    if hasattr(node, 'orelse'):
        try:
            # detect await clk() is else branch
            val = node.orelse[0].value
            comb_loop = isinstance(val,
                                   ast.Await) and (val.value.func.id == 'clk')
        except (AttributeError, IndexError):
            pass

    if comb_loop:
        length = find_var_length(node.iter, reg_finder.local_params)

        res = ResExpr(Uint[length](0))
        reg_name, reg_val = reg_finder.auto.new_auto_reg(res)
        reg_finder.regs[reg_name] = reg_val

        node.break_func = {'length': length, 'reg': reg_name}

    return comb_loop


class AutoReg:
    def __init__(self):
        self.regs = []
        self.variables = []

    def new_auto_var(self, val):
        name = f'auto_var_{len(self.variables)}'
        self.variables.append(val)
        return name, val

    def new_auto_reg(self, val):
        name = f'auto_reg_{len(self.regs)}'
        self.regs.append(val)
        return name, val


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

        self.auto = AutoReg()
        self.reg_loop_cb = [find_comb_loop]

    def promote_var_to_reg(self, name):
        val = self.variables[name]

        # wire, not register
        # TODO
        if not is_type(type(val)):
            return

        val = set_pg_type(val)

        self.regs[name] = ResExpr(val)

    def clean_variables(self):
        for reg in self.regs:
            if reg in self.variables:
                del self.variables[reg]

    def visit_AugAssign(self, node):
        self.promote_var_to_reg(node.target.id)

    def visit_For(self, node):
        names = find_for_target(node)

        register_var = False
        if not any([cb(node, self) for cb in self.reg_loop_cb]):
            register_var = find_async(node)

        for i, name in enumerate(names):
            if name in self.variables:
                self.promote_var_to_reg(name)
            else:
                if name not in self.intfs:
                    if i == 0:
                        length = find_var_length(node.iter, self.local_params)

                        if register_var:
                            self.regs[name] = ResExpr(Uint[bitw(length)](0))
                            hls_log().debug(
                                f'For loop iterator {name} registered with width {bitw(length)}'
                            )
                        else:
                            self.variables[name] = ResExpr(
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

        try:
            is_async = node.value.func.attr in ['get_nb', 'get']
        except AttributeError:
            is_async = False

        for name in names:
            if name in self.intf_outs:
                continue

            if name not in self.variables:
                if is_async:
                    hls_log().debug(
                        f'Assign to {name} not registered. Explicit initialization needed when using interface statements'
                    )
                    continue
                try:
                    self.variables[name] = eval_expression(
                        node.value, self.local_params)
                except NameError:
                    # wires/variables are not defined previously
                    self.variables[name] = node.value
            else:
                self.promote_var_to_reg(name)
