import ast
from . import Context, SyntaxError, node_visitor, nodes, visit_ast, visit_block
from pygears.typing import cast, Integer
from .utils import add_to_list


@node_visitor(ast.If)
def parse_if(node, ctx):
    test_expr = visit_ast(node.test, ctx)

    if isinstance(test_expr, nodes.ResExpr):
        body_stmts = []
        if bool(test_expr.val):
            for stmt in node.body:
                pydl_stmt = visit_ast(stmt, ctx)
                add_to_list(body_stmts, pydl_stmt)
        elif hasattr(node, 'orelse'):
            for stmt in node.orelse:
                pydl_stmt = visit_ast(stmt, ctx)
                add_to_list(body_stmts, pydl_stmt)

        if body_stmts:
            return body_stmts

        return None
    else:
        pydl_node = nodes.IfBlock(test=test_expr, stmts=[])
        visit_block(pydl_node, node.body, ctx)
        if hasattr(node, 'orelse') and node.orelse:
            pydl_node_else = nodes.ElseBlock(stmts=[])
            visit_block(pydl_node_else, node.orelse, ctx)
            top = nodes.ContainerBlock(stmts=[pydl_node, pydl_node_else])
            return top

        return pydl_node


@node_visitor(ast.While)
def _(node, ctx):
    pydl_node = nodes.Loop(test=visit_ast(node.test, ctx),
                               stmts=[],
                               multicycle=[])
    return visit_block(pydl_node, node.body, ctx)
