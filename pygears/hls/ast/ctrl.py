import ast
from . import Context, ir, node_visitor, visit_ast, visit_block
from pygears.lib.rng import qrange
from pygears.lib.union import select
from .stmt import assign_targets, extend_stmts
from .async_stmts import AsyncForContext
from .inline import call_gear
from .generators import parse_generator_expression, is_intf_list


@node_visitor(ast.If)
def _(node: ast.If, ctx: Context):
    test_expr = visit_ast(node.test, ctx)

    if isinstance(test_expr, ir.ResExpr):
        body_stmts = []
        if bool(test_expr.val):
            for stmt in node.body:
                ir_stmt = visit_ast(stmt, ctx)
                extend_stmts(body_stmts, ir_stmt)
        elif hasattr(node, 'orelse'):
            for stmt in node.orelse:
                ir_stmt = visit_ast(stmt, ctx)
                extend_stmts(body_stmts, ir_stmt)

        if body_stmts:
            return body_stmts

        return None
    else:
        ir_node = ir.HDLBlock()
        branch = ir_node.add_branch(ir.Branch(test=test_expr))
        visit_block(branch, node.body, ctx)
        if hasattr(node, 'orelse') and node.orelse:
            orelse = ir.BaseBlock()
            visit_block(orelse, node.orelse, ctx)
            if orelse.stmts:
                if len(orelse.stmts) == 1 and isinstance(orelse.stmts[0], ir.HDLBlock):
                    for b in orelse.stmts[0].branches:
                        ir_node.add_branch(b)
                else:
                    ir_node.add_branch(ir.Branch(stmts=orelse.stmts))

        if ir_node.branches[-1].test != ir.res_true:
            ir_node.add_branch()

        return ir_node


@node_visitor(ast.While)
def _(node: ast.While, ctx: Context):
    ir_node = ir.LoopBlock(in_cond=visit_ast(node.test, ctx), stmts=[])
    return visit_block(ir_node, node.body, ctx)


def intf_loop(node, intfs, targets, ctx: Context, enumerated):
    rng_intf, stmts = call_gear(qrange, [ir.ResExpr(len(intfs))], {}, ctx)
    ctx.ir_parent_block.stmts.extend(stmts)

    with AsyncForContext(rng_intf, ctx) as stmts:
        rng_iter = ir.SubscriptExpr(ir.Component(rng_intf.obj, 'data'),
                                    ir.ResExpr(0))
        select_intf, call_stmts = call_gear(select,
                                            args=[rng_iter] + intfs,
                                            kwds={},
                                            ctx=ctx)
        ctx.ir_parent_block.stmts.extend(call_stmts)

        if enumerated:
            intf_var_name = targets.operands[1].name
        else:
            intf_var_name = targets.name

        ctx.local_namespace[intf_var_name] = select_intf

        if enumerated:
            extend_stmts(
                ctx.ir_parent_block.stmts,
                assign_targets(
                    ctx, targets.operands[0],
                    ir.SubscriptExpr(ir.Component(rng_intf.obj, 'data'),
                                     ir.ResExpr(0)), ir.Variable))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            extend_stmts(ctx.ir_parent_block.stmts, res_stmt)

        return stmts


@node_visitor(ast.For)
def _(node: ast.For, ctx: Context):
    out_intf_ref, targets, gen_name = parse_generator_expression(node, ctx)

    if is_intf_list(out_intf_ref):
        return intf_loop(node, out_intf_ref.operands, targets, ctx,
                         getattr(out_intf_ref, 'enumerated', False))

    block = ir.LoopBlock(
        stmts=[ir.AssignValue(targets, ir.GenNext(ctx.ref(gen_name)))],
        exit_cond=ir.GenDone(gen_name))

    visit_block(block, node.body, ctx)

    block.stmts.append(ir.ExprStatement(ir.GenAck(gen_name)))

    return block
