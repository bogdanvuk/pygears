import ast
from . import Context, HLSSyntaxError, ir, node_visitor, visit_ast, ir_utils
from pygears import Intf
from .stmt import infer_targets


def is_intf_list(node):
    if isinstance(node, ir.ConcatExpr):
        return all(ir_utils.is_intf_id(v) for v in node.operands)

    if not isinstance(node, ir.ResExpr):
        return False

    if not isinstance(node.val, list):
        return False


def parse_generator_expression(node, ctx):
    targets = visit_ast(node.target, ctx)

    out_intf_ref = visit_ast(node.iter, ctx)

    if is_intf_list(out_intf_ref):
        return out_intf_ref, targets, None

    gen_name = ctx.find_unique_name('_gen')
    ctx.scope[gen_name] = ir.Generator(gen_name, out_intf_ref)

    infer_targets(ctx, targets, out_intf_ref)

    return out_intf_ref, targets, gen_name


@node_visitor(ast.GeneratorExp)
def _(node: ast.GeneratorExp, ctx: Context):
    # out_intf_ref, targets, gen_name = parse_generator_expression(node.generators[0], ctx)

    # breakpoint()
    raise HLSSyntaxError(f"Unsupported language construct", node.lineno)
