import ast

import hdl_types as ht
from pygears.typing import is_type

from .hdl_utils import (eval_expression, find_assign_target, find_for_target,
                        set_pg_type)
from .inst import svgen_log


class RegFinder(ast.NodeVisitor):
    def __init__(self, gear, intf_args, intf_outs):
        self.regs = {}
        self.variables = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params,
            **intf_args
        }
        self.intf_outs = intf_outs.keys()

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
            del self.variables[reg]

    def visit_AugAssign(self, node):
        self.promote_var_to_reg(node.target.id)

    def visit_For(self, node):
        names = find_for_target(node)

        for name in names:
            if name in self.variables:
                self.promote_var_to_reg(name)
            else:
                svgen_log().warning(
                    f'For loop interator {name} not registered')

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
