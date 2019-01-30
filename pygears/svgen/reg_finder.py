import ast
import hdl_types as ht

from pygears.typing import Int, Uint, is_type
from .hdl_ast import eval_expression, find_vararg_input


class RegFinder(ast.NodeVisitor):
    def __init__(self, gear):
        self.regs = {}
        self.variables = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params,
            **find_vararg_input(gear)
        }

    def promote_var_to_reg(self, name):
        val = self.variables[name]

        # wire, not register
        if isinstance(val, ast.AST):
            return

        if not is_type(type(val)):
            if val < 0:
                val = Int(val)
            else:
                val = Uint(val)

        self.regs[name] = ht.ResExpr(val)

    def clean_variables(self):
        for r in self.regs:
            del self.variables[r]

    def visit_AugAssign(self, node):
        self.promote_var_to_reg(node.target.id)

    def visit_For(self, node):
        if isinstance(node.target, ast.Tuple):
            for el in node.target.elts:
                if el.id in self.variables:
                    self.promote_var_to_reg(el.id)
        else:
            self.promote_var_to_reg(node.target.id)

        for stmt in node.body:
            self.visit(stmt)

    def visit_Assign(self, node):
        name = node.targets[0].id
        if name not in self.variables:
            try:
                self.variables[name] = eval_expression(node.value,
                                                       self.local_params)
            except NameError:
                # wires/variables are not defined previously
                self.variables[name] = node.value
        else:
            self.promote_var_to_reg(name)
