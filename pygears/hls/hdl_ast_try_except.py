import ast

from . import hdl_types as ht
from .hdl_utils import VisitError, interface_operations

# 1st key: exception type
# 2nd key: method which can cause the exception
# value: block type
INTF_EXCEPTIONS = {'QueueEmpty': {'get_nb': ht.IntfBlock}}


def find_exception(ex_type, method_name):
    for supported_names, supported_values in INTF_EXCEPTIONS.items():
        if ex_type == supported_names:
            if method_name in supported_values:
                return supported_values[method_name]

    return None


class HdlAstTryExcept(ast.NodeVisitor):
    def __init__(self, ast_v):
        self.ast_v = ast_v
        self.exception_names = []

    def find_condition(self, node):
        self.exception_names = [handler.type.id for handler in node.handlers]

        cond = None
        for stmt in node.body:
            cond = self.visit(stmt)
            if cond is not None:
                break

        self.exception_names = []
        return cond

    def visit_Assign(self, node):
        flag, intf_val = interface_operations(node.value)
        if flag:
            intf_name, intf_method = intf_val
            for curr_ex in self.exception_names:
                block = find_exception(curr_ex, intf_method)
                if block is not None:
                    name = self.ast_v.get_context_var(intf_name)
                    if isinstance(name, ht.IntfExpr):
                        intf = ht.IntfExpr(intf=name.intf, context='valid')
                        return block(intf=intf, stmts=[])

                    raise VisitError(
                        'Exceptions only supported for interfaces for now..')

        return None
