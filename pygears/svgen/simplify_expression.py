from functools import partial, reduce

import sympy

import hdl_types as ht
from pygears.typing import Bool

from .hdl_stmt_types import AssignValue, CombSeparateStmts
from .hdl_utils import VisitError
from .inst_visit import InstanceVisitor


class SameConditions:
    def __init__(self, block):
        self.same_num = 0
        self.conditions = {}
        self.names = []
        self.unique_values = []
        self.unique_names = {}

        self.set_conditions(block.stmts)
        self.find_same_names()

    def set_conditions(self, stmts):
        for stmt in stmts:
            if stmt.val in self.unique_values:
                self.set_same_cond(stmt)
            else:
                self.set_new_cond(stmt)

    def set_same_cond(self, cond):
        idx = self.unique_values.index(cond.val)
        self.names[idx].append(cond.target)

    def set_new_cond(self, cond):
        self.unique_values.append(cond.val)
        self.names.append([cond.target])

    def find_same_names(self):
        cnt = 0
        for name in self.names:
            if len(name) == 1:
                self.unique_names[name[0]] = name
            else:
                new_name = ht.COND_NAME.substitute(
                    cond_type='same', block_id=cnt)
                cnt += 1
                self.unique_names[new_name] = name

    def get_clean_conds(self):
        stmts = []
        assert len(self.unique_names.keys()) == len(self.unique_values)
        for name, val in zip(self.unique_names.keys(), self.unique_values):
            stmts.append(AssignValue(target=name, val=val))

        for same, names in self.unique_names.items():
            if len(names) > 1:
                for name in names:
                    stmts.append(AssignValue(target=name, val=same))

        return CombSeparateStmts(stmts=stmts)


class Hdl2Sym(ht.TypeVisitor):
    def __init__(self, same_names=None):
        self.same_names = same_names
        self.special_symbols = {}

    def get_special(self, node):
        if node in self.special_symbols.values():
            for name, val in self.special_symbols.items():
                if val == node:
                    return sympy.symbols(name)
            return None

        symbol_id = len(self.special_symbols.keys())
        name = f'spec_{symbol_id}'
        self.special_symbols[name] = node
        return sympy.symbols(name)

    def visit_int(self, node):
        return node

    def visit_str(self, node):
        if self.same_names:
            if node not in self.same_names.keys():
                for key, val in self.same_names.items():
                    if node in val:
                        return sympy.symbols(key)

        return sympy.symbols(node)

    def generic_visit(self, node):
        return self.get_special(node)

    def visit_ResExpr(self, node):
        return int(node.val)

    def visit_UnaryOpExpr(self, node):
        operand = self.visit(node.operand)

        if node.operator == '!':
            return sympy.Not(operand)

        return None

    def visit_BinOpExpr(self, node):
        if node.operator not in ht.BOOLEAN_OPERATORS:
            return self.get_special(node)

        operands = []
        for op in node.operands:
            operands.append(self.visit(op))

        if node.operator == '&&':
            return sympy.And(*operands)

        if node.operator == '||':
            return sympy.Or(*operands)

        raise VisitError(f'Operator not supported, {node.operator}')


class Sym2Hdl(InstanceVisitor):
    def __init__(self, special_symbols):
        self.special_symbols = special_symbols

    def visit_Symbol(self, node):
        sym = str(node)

        if sym in self.special_symbols:
            return self.special_symbols[sym]

        return sym

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

        return ht.UnaryOpExpr(operands[0], operator)


def simplify_expr(expr, same_names=None):
    hdl_v = Hdl2Sym(same_names)
    sym_expr = hdl_v.visit(expr)
    res = sympy.simplify_logic(sym_expr)
    sym_v = Sym2Hdl(hdl_v.special_symbols)
    res_expr = sym_v.visit(res)
    return res_expr


def simplify_assigns(stmts):
    same = SameConditions(stmts)

    for i, stmt in enumerate(same.unique_values):
        same.unique_values[i] = simplify_expr(stmt, same.unique_names)

    return same.get_clean_conds()
