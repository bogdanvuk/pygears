import ast
from . import Context, SyntaxError, node_visitor, ir, visit_ast, visit_block
from pygears import Intf
from pygears.typing import cast, Integer, Bool, typeof, Queue
from pygears.lib.rng import qrange
from pygears.lib.union import select
from .utils import add_to_list
from .stmt import assign_targets, infer_targets
from .async_stmts import AsyncForContext
from .inline import form_gear_args, call_gear


def is_intf_id(expr):
    return (isinstance(expr, ir.Name) and isinstance(expr.obj, ir.Variable)
            and isinstance(expr.obj.val, Intf))


def is_intf_list(node):
    if isinstance(node, ir.ConcatExpr):
        return all(is_intf_id(v) for v in node.operands)

    if not isinstance(node, ir.ResExpr):
        return False

    if not isinstance(node.val, list):
        return False

    return all(isinstance(v, ir.Interface) for v in node.val)


def parse_generator_expression(node, ctx):
    targets = visit_ast(node.target, ctx)

    out_intf_ref = visit_ast(node.iter, ctx)

    if is_intf_list(out_intf_ref):
        return out_intf_ref, None, None

    gen_name = ctx.find_unique_name('_gen')
    ctx.scope[gen_name] = ir.Generator(gen_name, out_intf_ref)

    infer_targets(ctx, targets, out_intf_ref.dtype, ir.Variable)

    return out_intf_ref, targets, gen_name


@node_visitor(ast.GeneratorExp)
def _(node: ast.GeneratorExp, ctx: Context):
    # out_intf_ref, targets, gen_name = parse_generator_expression(node.generators[0], ctx)

    breakpoint()
    raise SyntaxError(f"Unsupported language construct", node.lineno)
