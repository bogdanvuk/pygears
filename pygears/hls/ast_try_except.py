import ast

from .ast_parse import parse_ast, parse_block
from .hls_blocks import ContainerBlock, IfBlock, IntfBlock
from .hls_expressions import IntfDef, create_oposite
from .utils import VisitError, interface_operations

# 1st key: exception type
# 2nd key: method which can cause the exception
# value: block type
INTF_EXCEPTIONS = {'QueueEmpty': {'get_nb': IntfBlock}}


@parse_ast.register(ast.Try)
def parse_try(node, module_data):
    assert len(
        node.handlers) == 1, f'Try/except block must only except one exception'
    # try_block = self._find_condition(node)
    try_block = HdlAstTryExcept(module_data).find_condition(node)
    if try_block is None:
        raise VisitError('No condition found for try/except block')

    parse_block(try_block, node.body, module_data)

    except_block = IfBlock(
        _in_cond=create_oposite(try_block.in_cond), stmts=[])
    parse_block(except_block, node.handlers[0].body, module_data)

    return ContainerBlock(stmts=[try_block, except_block])


def find_exception(ex_type, method_name):
    for supported_names, supported_values in INTF_EXCEPTIONS.items():
        if ex_type == supported_names:
            if method_name in supported_values:
                return supported_values[method_name]

    return None


class HdlAstTryExcept(ast.NodeVisitor):
    def __init__(self, module_data):
        self.data = module_data
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
                    intf = self.data.hdl_locals.get(intf_name, None)
                    if isinstance(intf, IntfDef):
                        new_intf = IntfDef(
                            intf=intf.intf, _name=intf.name, context='valid')
                        return block(intf=new_intf, stmts=[])

                    raise VisitError(
                        'Exceptions only supported for interfaces for now..')

        return None
