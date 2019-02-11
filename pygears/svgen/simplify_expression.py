import hdl_types as ht
from functools import reduce, partial
from .inst_visit import InstanceVisitor
from pygears.typing import Bool
import sympy


class Hdl2Sym(ht.TypeVisitor):
    def __init__(self):
        self.special_symbols = {}

    def get_special(self, node):
        id = len(self.special_symbols.keys())
        name = f'spec_{id}'
        self.special_symbols[name] = node
        return sympy.symbols(name)

    def visit_int(self, node):
        return node

    def visit_str(self, node):
        return sympy.symbols(node)

    def generic_visit(self, node):
        return self.get_special(node)

    def visit_ResExpr(self, node):
        return int(node.val)

    def visit_UnaryOpExpr(self, node):
        operand = self.visit(node.operand)

        if node.operator == '!':
            return sympy.Not(operand)

    def visit_BinOpExpr(self, node):
        if node.operator not in ht.boolean_operators:
            return self.get_special(node)

        operands = []
        for op in node.operands:
            operands.append(self.visit(op))

        if node.operator == '&&':
            return sympy.And(*operands)

        if node.operator == '||':
            return sympy.Or(*operands)

        assert False, f'Operator not supported, {node.operator}'


class Sym2Hdl(InstanceVisitor):
    def __init__(self, special_symbols):
        self.special_symbols = special_symbols

    def visit_Symbol(self, node):
        s = str(node)
        if s in self.special_symbols:
            return self.special_symbols[s]
        else:
            return s

    def visit_BooleanFalse(self, node):
        return ht.ResExpr(Bool(False))

    def visit_BooleanTrue(self, node):
        return ht.ResExpr(Bool(True))

    def visit_Not(self, node):
        return self.visit_opexpr(node, '!')

    def visit_And(self, node):
        return self.visit_opexpr(node, '&&')

    def visit_Or(self, node):
        return self.visit_opexpr(node, '||')

    def visit_opexpr(self, node, operator):
        operands = [self.visit(arg) for arg in reversed(node.args)]
        if len(operands) > 1:
            return reduce(
                partial(ht.binary_expr, operator=operator), operands, None)
        else:
            return ht.UnaryOpExpr(operands[0], operator)


def simplify_expr(expr):
    hdl_v = Hdl2Sym()
    sym_expr = hdl_v.visit(expr)
    res = sympy.simplify_logic(sym_expr)
    sym_v = Sym2Hdl(hdl_v.special_symbols)
    res_expr = sym_v.visit(res)
    return res_expr
