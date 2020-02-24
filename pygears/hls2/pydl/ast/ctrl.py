import ast
from . import Context, SyntaxError, node_visitor, nodes, visit_ast, visit_block
from pygears.typing import cast, Integer, Bool, typeof, Queue
from pygears.lib.rng import qrange
from pygears.lib.union import select
from .utils import add_to_list
from .stmt import assign_targets, infer_targets
from .async_stmts import AsyncForContext
from .inline import form_gear_args, call_gear


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
            top = nodes.ContainerBlock(stmts=[])
            visit_block(top, node.orelse, ctx)

            if isinstance(top.stmts[0], nodes.IfBlock):
                top.stmts.insert(0, pydl_node)
            elif isinstance(top.stmts[0], nodes.ContainerBlock):
                top.stmts = [pydl_node] + top.stmts[0].stmts
            else:
                top.stmts = [pydl_node, nodes.ElseBlock(stmts=top.stmts)]

            return top

        return pydl_node


@node_visitor(ast.While)
def _(node: ast.While, ctx: Context):
    pydl_node = nodes.Loop(test=visit_ast(node.test, ctx), stmts=[])
    return visit_block(pydl_node, node.body, ctx)


def is_intf_list(node):
    if not isinstance(node, nodes.ResExpr):
        return False

    if not isinstance(node.val, list):
        return False

    return all(isinstance(v, nodes.Interface) for v in node.val)


def intf_loop(node, intfs, targets, ctx: Context, enumerated):
    rng_intf, stmts = call_gear(qrange, [nodes.ResExpr(len(intfs))], {}, ctx)
    ctx.pydl_parent_block.stmts.extend(stmts)

    with AsyncForContext(rng_intf, ctx) as stmts:
        rng_iter = nodes.SubscriptExpr(nodes.Component(rng_intf.obj, 'data'),
                                       nodes.ResExpr(0))
        select_intf, call_stmts = call_gear(select,
                                            args=[rng_iter] + intfs,
                                            kwds={},
                                            ctx=ctx)
        ctx.pydl_parent_block.stmts.extend(call_stmts)

        if enumerated:
            intf_var_name = targets.operands[1].name
        else:
            intf_var_name = targets.name

        ctx.local_namespace[intf_var_name] = select_intf

        if enumerated:
            add_to_list(
                ctx.pydl_parent_block.stmts,
                assign_targets(
                    ctx, targets.operands[0],
                    nodes.SubscriptExpr(nodes.Component(rng_intf.obj, 'data'),
                                        nodes.ResExpr(0)), nodes.Variable))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            add_to_list(ctx.pydl_parent_block.stmts, res_stmt)

        return stmts


@node_visitor(ast.For)
def _(node: ast.For, ctx: Context):
    targets = visit_ast(node.target, ctx)

    out_intf_ref = visit_ast(node.iter, ctx)

    if is_intf_list(out_intf_ref):
        return intf_loop(node, out_intf_ref.val, targets, ctx,
                         getattr(out_intf_ref, 'enumerated', False))

    gen_name = ctx.find_unique_name('_gen')
    ctx.scope[gen_name] = nodes.Generator(gen_name, out_intf_ref)

    infer_targets(ctx, targets, out_intf_ref.dtype, nodes.Variable)

    block = nodes.Loop(
        test=nodes.GenLive(ctx.ref(gen_name)),
        stmts=[nodes.Assign(nodes.GenNext(ctx.ref(gen_name)), targets)])

    visit_block(block, node.body, ctx)

    return block

    # breakpoint()

    # with AsyncForContext(out_intf_ref, ctx) as stmts:
    #     data = nodes.Component(out_intf_ref.obj, 'data')
    #     if not getattr(out_intf_ref, 'eot_to_data', False):
    #         data = nodes.SubscriptExpr(data, nodes.ResExpr(0))

    #     add_to_list(ctx.pydl_parent_block.stmts,
    #                 assign_targets(ctx, targets, data, nodes.Variable))

    #     for stmt in node.body:
    #         res_stmt = visit_ast(stmt, ctx)
    #         add_to_list(ctx.pydl_parent_block.stmts, res_stmt)

    #     return stmts
