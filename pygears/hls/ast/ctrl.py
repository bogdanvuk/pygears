import ast
from . import Context, ir, node_visitor, visit_ast, visit_block
from pygears.lib.rng import qrange
from pygears.lib.union import select
from .utils import add_to_list
from .stmt import assign_targets
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
                add_to_list(body_stmts, ir_stmt)
        elif hasattr(node, 'orelse'):
            for stmt in node.orelse:
                ir_stmt = visit_ast(stmt, ctx)
                add_to_list(body_stmts, ir_stmt)

        if body_stmts:
            return body_stmts

        return None
    else:
        ir_node = ir.HDLBlock(in_cond=test_expr, stmts=[])
        visit_block(ir_node, node.body, ctx)
        if hasattr(node, 'orelse') and node.orelse:
            top = ir.IfElseBlock(stmts=[])
            visit_block(top, node.orelse, ctx)

            if isinstance(top.stmts[0], ir.HDLBlock):
                top.stmts.insert(0, ir_node)
            elif isinstance(top.stmts[0], ir.IfElseBlock):
                top.stmts = [ir_node] + top.stmts[0].stmts
            else:
                top.stmts = [ir_node, ir.HDLBlock(stmts=top.stmts)]

            return top

        return ir_node


@node_visitor(ast.While)
def _(node: ast.While, ctx: Context):
    ir_node = ir.LoopBlock(test=visit_ast(node.test, ctx), stmts=[])
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
            add_to_list(
                ctx.ir_parent_block.stmts,
                assign_targets(
                    ctx, targets.operands[0],
                    ir.SubscriptExpr(ir.Component(rng_intf.obj, 'data'),
                                     ir.ResExpr(0)), ir.Variable))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            add_to_list(ctx.ir_parent_block.stmts, res_stmt)

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
