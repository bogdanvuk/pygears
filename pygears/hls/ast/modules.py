import ast
from . import Context, FuncContext, SyntaxError, ir, node_visitor, visit_ast, visit_block


@node_visitor(ast.AsyncFunctionDef)
def parse_async_func(node, ctx: Context):
    return visit_block(ir.HDLBlock(stmts=[]), node.body, ctx)


# @node_visitor(ast.Lambda)
# def _(node, ctx: FuncContext):
#     if not isinstance(ctx, FuncContext):
#         raise Exception('Unsupported')

#     return visit_block(
#         ir.FuncBlock(stmts=[],
#                      args=ctx.args,
#                      name=ctx.funcref.name,
#                      ret_dtype=ctx.ret_dtype), node.body, ctx)


@node_visitor((ast.Lambda, ast.FunctionDef))
def _(node, ctx: FuncContext):
    if not isinstance(ctx, FuncContext):
        raise Exception('Unsupported')

    block = ir.FuncBlock(stmts=[],
                         args=ctx.args,
                         name=ctx.funcref.name,
                         ret_dtype=ctx.ret_dtype)

    ret = visit_block(block, node.body, ctx)

    #TODO: Why is this necessary?
    block.ret_dtype = ctx.ret_dtype

    return ret
