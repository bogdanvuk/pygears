import ast

import hdl_types as ht

from .hdl_ast import eval_expression, set_pg_type


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
        if isinstance(val, ast.AST):
            return

        val = set_pg_type(val)

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
            assert node.target.id in self.variables, 'Loop iterator not registered'
            self.promote_var_to_reg(node.target.id)

        for stmt in node.body:
            self.visit(stmt)

    def visit_Assign(self, node):
        if hasattr(node.targets[0], 'id'):
            name = node.targets[0].id
        elif hasattr(node.targets[0], 'value'):
            name = node.targets[0].value.id
        else:
            assert False, 'Unknown assignment type'

        if name in self.intf_outs:
            return

        if name not in self.variables:
            try:
                self.variables[name] = eval_expression(node.value,
                                                       self.local_params)
            except NameError:
                # wires/variables are not defined previously
                self.variables[name] = node.value
        else:
            self.promote_var_to_reg(name)
