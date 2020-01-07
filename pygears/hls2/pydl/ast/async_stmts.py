import ast
from . import node_visitor, nodes, visit_block, visit_ast, Context, SyntaxError
from .cast import resolve_cast_func
from .utils import add_to_list
from .stmt import assign_targets


@node_visitor(ast.AsyncFunctionDef)
def parse_async_func(node, ctx: Context):
    return visit_block(nodes.Module(stmts=[]), node.body, ctx)


def is_target_id(node):
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


# TODO: Revisit cast_return, maybe it can be more general
from pygears.typing import typeof, Queue, Tuple


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)
    if isinstance(arg_nodes, list):
        assert len(arg_nodes) == out_num
        input_vars = arg_nodes
    elif isinstance(arg_nodes, nodes.OperandVal) and out_num > 1:
        intf = arg_nodes.op
        assert len(intf.intf) == out_num
        input_vars = []
        for i in range(len(intf.intf)):
            input_vars.append(
                nodes.SubscriptExpr(val=intf, index=nodes.ResExpr(i)))
    else:
        assert out_num == 1
        input_vars = [arg_nodes]

    args = []
    for arg, intf in zip(input_vars, out_ports):
        port_t = intf.dtype
        if typeof(port_t, Queue) or typeof(port_t, Tuple):
            if isinstance(arg, nodes.ConcatExpr) and arg.dtype != port_t:
                for i in range(len(arg.operands)):
                    if isinstance(arg.operands[i], nodes.CastExpr) and (
                            arg.operands[i].cast_to == port_t[i]):
                        pass
                    else:
                        arg.operands[i] = resolve_cast_func(
                            arg.operands[i], port_t[i])

            args.append(arg)
        else:
            if arg.dtype != port_t:
                args.append(resolve_cast_func(arg, port_t))
            else:
                args.append(arg)

    return args


@node_visitor(ast.Yield)
def parse_yield(node, ctx):
    yield_expr = visit_ast(node.value, ctx)

    try:
        ret = cast_return(yield_expr, ctx.gear.out_ports)
    except TypeError as e:
        raise TypeError(
            f"{str(e)}\n    - when casting output value to the output type")

    return nodes.Yield(stmts=ret,
                       ports=[nodes.Interface(p) for p in ctx.gear.out_ports])


@node_visitor(ast.withitem)
def withitem(node: ast.withitem, ctx: Context):
    assert isinstance(ctx.pydl_parent_bock, nodes.IntfBlock)

    intf = visit_ast(node.context_expr, ctx)
    targets = visit_ast(node.optional_vars, ctx)

    if not isinstance(targets, tuple):
        targets = (targets, )

    ass_targets = []
    for t in targets:
        var = nodes.Variable(t.name, intf.dtype)
        ctx.scope[t.name] = var
        ass_targets.append(nodes.Name(t.name, var, t.ctx))

    return intf, ass_targets


@node_visitor(ast.AsyncWith)
def asyncwith(node, ctx: Context):
    pydl_node = nodes.IntfBlock(intfs=[], stmts=[])
    ctx.pydl_block_closure.append(pydl_node)

    assigns = [visit_ast(i, ctx) for i in node.items]

    for intf, targets in assigns:
        pydl_node.intfs.append(intf)
        if len(targets) == 1:
            pydl_node.stmts.append(
                nodes.Assign(targets[0], nodes.InterfacePull(intf)))
        else:
            raise SyntaxError

    for stmt in node.body:
        res_stmt = visit_ast(stmt, ctx)
        add_to_list(pydl_node.stmts, res_stmt)

    ctx.pydl_block_closure.pop()

    return pydl_node


@node_visitor(ast.AsyncFor)
def AsyncFor(node, ctx: Context):
    pydl_node = nodes.IntfLoop(intf=visit_ast(node.iter, ctx).obj,
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
