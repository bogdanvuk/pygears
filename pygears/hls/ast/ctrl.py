import ast
from . import Context, ir, node_visitor, visit_ast, visit_block
from pygears.lib.rng import qrange
from pygears.lib.union import select
from .stmt import assign_targets, extend_stmts
from .async_stmts import AsyncForContext, merge_cond_alias_map
from .inline import call_gear
from .generators import parse_generator_expression, is_intf_list


@node_visitor(ast.If)
def _(node: ast.If, ctx: Context):
    test_expr = visit_ast(node.test, ctx)

    ir_node = ir.HDLBlock()
    if test_expr != ir.res_false:
        branch = ir_node.add_branch(ir.Branch(test=test_expr))
        visit_block(branch, node.body, ctx)

    if test_expr != ir.res_true and hasattr(node, 'orelse') and node.orelse:
        orelse = ir.BaseBlock()
        visit_block(orelse, node.orelse, ctx)
        if orelse.stmts:
            if len(orelse.stmts) == 1 and isinstance(orelse.stmts[0], ir.HDLBlock):
                for b in orelse.stmts[0].branches:
                    ir_node.add_branch(b)
            else:
                branch = ir_node.add_branch(ir.Branch(stmts=orelse.stmts))
                ctx.closure_alias_maps[branch] = ctx.closure_alias_maps[orelse]

    if len(ir_node.branches) == 1 and ir_node.branches[0].test == ir.res_true:
        ctx.alias_map.update(ctx.closure_alias_maps[ir_node.branches[0]])
        return ir_node.branches[0].stmts

    for b in ir_node.branches:
        merge_cond_alias_map(b, ctx)

    if not ir_node.branches:
        return []

    return ir_node


@node_visitor(ast.While)
def _(node: ast.While, ctx: Context):
    test = visit_ast(node.test, ctx)
    if test == ir.res_false:
        return None

    ir_node = ir.HDLBlock()

    ir_node = ir.LoopBlock()
    loop = visit_block(ir_node, node.body, ctx)

    ctx.closures.append(ir_node)
    ir_node.test = visit_ast(node.test, ctx)
    ctx.closures.pop()

    merge_cond_alias_map(loop, ctx)

    maybe_loop = ir.HDLBlock([ir.Branch(test=test, stmts=[loop])])

    return maybe_loop


def intf_loop(node, intfs, targets, ctx: Context, enumerated):
    rng_intf, stmts = call_gear(qrange, [ir.ResExpr(len(intfs))], {}, ctx)
    ctx.ir_parent_block.stmts.extend(stmts)

    with AsyncForContext(rng_intf, ctx) as stmts:
        rng_iter = ir.SubscriptExpr(ir.Component(rng_intf.obj, 'data'), ir.ResExpr(0))
        select_intf, call_stmts = call_gear(select, args=[rng_iter] + intfs, kwds={}, ctx=ctx)
        ctx.ir_parent_block.stmts.extend(call_stmts)

        if enumerated:
            intf_var_name = targets.operands[1].name
        else:
            intf_var_name = targets.name

        ctx.local_namespace[intf_var_name] = select_intf

        if enumerated:
            extend_stmts(
                ctx.ir_parent_block.stmts,
                assign_targets(ctx, targets.operands[0],
                               ir.SubscriptExpr(ir.Component(rng_intf.obj, 'data'), ir.ResExpr(0))))

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

    block = ir.LoopBlock(stmts=[ir.AssignValue(targets, ir.GenNext(gen_name))],
                         test=ir.GenDone(gen_name))

    visit_block(block, node.body, ctx)

    block.stmts.append(ir.ExprStatement(ir.GenAck(gen_name)))

    merge_cond_alias_map(block, ctx)

    return [ir.ExprStatement(ir.GenInit(ctx.ref(gen_name))), block]
