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
        self.data = ast_v.data
        self.exception_names = []

    def _find_condition(self, node):
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
                    intf = self.data.hdl_locals.get(intf_name, None)
                    if isinstance(intf, ht.IntfExpr):
                        new_intf = ht.IntfExpr(intf=intf.intf, context='valid')
                        return block(intf=new_intf, stmts=[])
                    if isinstance(intf, ht.IntfDef):
                        new_intf = ht.IntfDef(
                            intf=intf.intf, name=intf.name, context='valid')
                        return block(intf=new_intf, stmts=[])

                    raise VisitError(
                        'Exceptions only supported for interfaces for now..')

        return None

    def analyze(self, node):
        assert len(
            node.
            handlers) == 1, f'Try/except block must only except one exception'
        try_block = self._find_condition(node)
        if try_block is None:
            raise VisitError('No condition found for try/except block')

        self.ast_v.visit_block(try_block, node.body)

        except_block = ht.IfBlock(
            _in_cond=ht.create_oposite(try_block.in_cond), stmts=[])
        self.ast_v.visit_block(except_block, node.handlers[0].body)

        return ht.ContainerBlock(stmts=[try_block, except_block])
