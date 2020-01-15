import ast
from . import Context, SyntaxError, node_visitor, nodes, visit_ast, visit_block
from pygears.typing import cast, Integer, Bool, typeof, Queue
from .utils import add_to_list
from .stmt import assign_targets


@node_visitor(ast.If)
def _(node: ast.If, ctx: Context):
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
def _(node: ast.While, ctx: Context):
    pydl_node = nodes.Loop(test=visit_ast(node.test, ctx),
                           stmts=[],
                           multicycle=[])
    return visit_block(pydl_node, node.body, ctx)


@node_visitor(ast.For)
def _(node: ast.For, ctx: Context):
    out_intf = visit_ast(node.iter, ctx).obj

    if not typeof(out_intf.dtype, Queue):
        raise Exception('Unsupported return data type for for loop')

    # in_intf = ctx.submodules[-1].in_ports[0]

    pydl_node = nodes.IntfLoop(intf=out_intf,
                               stmts=[],
                               multicycle=[])
    ctx.pydl_block_closure.append(pydl_node)

    targets = visit_ast(node.target, ctx)

    add_to_list(
        pydl_node.stmts,
        assign_targets(ctx, targets, nodes.InterfacePull(pydl_node.intf),
                       nodes.Variable))

    for stmt in node.body:
        res_stmt = visit_ast(stmt, ctx)
        add_to_list(pydl_node.stmts, res_stmt)

    ctx.pydl_block_closure.pop()

    return pydl_node

    # out_intf = visit_ast(node.iter, ctx).obj

    # in_intf = ctx.submodules[-1].in_ports[0]

    # last_var_name = f'{ctx.submodules[-1].gear.basename}_last'
    # ctx.scope[last_var_name] = nodes.Variable(last_var_name, dtype=Bool)

    # test = nodes.BinOpExpr((
    #     nodes.Component(in_intf, 'valid'),
    #     nodes.UnaryOpExpr(ctx.ref(last_var_name), '!'),
    # ), '&&')

    # pydl_node = nodes.Loop(test=test, stmts=[], multicycle=[])
    # ctx.pydl_block_closure.append(pydl_node)

    # targets = visit_ast(node.target, ctx)

    # add_to_list(
    #     pydl_node.stmts,
    #     assign_targets(ctx, targets, nodes.InterfacePull(out_intf),
    #                    nodes.Variable))

    # pydl_node.stmts.append(
    #     nodes.Assign(
    #         nodes.ArrayOpExpr(
    #             nodes.SubscriptExpr(nodes.Component(out_intf, 'data'),
    #                                 nodes.ResExpr(-1)), '&'),
    #         ctx.ref(last_var_name, 'store'),
    #     ))

    # for stmt in node.body:
    #     res_stmt = visit_ast(stmt, ctx)
    #     add_to_list(pydl_node.stmts, res_stmt)

    # ctx.pydl_block_closure.pop()

    # return [
    #     nodes.Assign(nodes.ResExpr(Bool(False)),
    #                  ctx.ref(last_var_name, 'store')), pydl_node
    # ]
