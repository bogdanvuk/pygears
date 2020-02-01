import ast
from . import node_visitor, nodes, visit_block, visit_ast, Context, SyntaxError, FuncContext
from .cast import resolve_cast_func
from .utils import add_to_list
from .stmt import assign_targets


@node_visitor(ast.AsyncFunctionDef)
def parse_async_func(node, ctx: Context):
    return visit_block(nodes.Module(stmts=[]), node.body, ctx)


@node_visitor(ast.FunctionDef)
def _(node, ctx: FuncContext):
    if not isinstance(ctx, FuncContext):
        raise Exception('Unsupported')

    return visit_block(
        nodes.Function(stmts=[],
                       name=ctx.funcref.name,
                       args=ctx.args,
                       ret_dtype=ctx.ret_dtype), node.body, ctx)


def is_target_id(node):
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


# TODO: Revisit cast_return, maybe it can be more general
from pygears.typing import typeof, Queue, Tuple, Array


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)
    if isinstance(arg_nodes, (list, tuple)):
        assert len(arg_nodes) == out_num
        input_vars = arg_nodes
    elif isinstance(arg_nodes, nodes.Name) and out_num > 1:
        var = arg_nodes.obj
        assert len(var.dtype) == out_num
        input_vars = []
        for i in range(len(var.dtype)):
            input_vars.append(
                nodes.SubscriptExpr(val=arg_nodes, index=nodes.ResExpr(i)))
    else:
        assert out_num == 1
        input_vars = [arg_nodes]

    args = []
    for arg, intf in zip(input_vars, out_ports):
        port_t = intf.dtype
        if typeof(port_t, (Queue, Tuple, Array)):
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

    return nodes.TupleExpr(args)


@node_visitor(ast.Yield)
def parse_yield(node, ctx):
    yield_expr = visit_ast(node.value, ctx)

    try:
        ret = cast_return(yield_expr, ctx.gear.out_ports)
    except TypeError as e:
        raise TypeError(
            f"{str(e)}\n    - when casting output value to the output type")

    return nodes.Yield(ret, ports=ctx.out_ports)


@node_visitor(ast.withitem)
def withitem(node: ast.withitem, ctx: Context):
    # assert isinstance(ctx.pydl_parent_block, nodes.IntfBlock)

    intf = visit_ast(node.context_expr, ctx)
    targets = visit_ast(node.optional_vars, ctx)

    if isinstance(intf, nodes.ConcatExpr):
        data = nodes.ConcatExpr(
            [nodes.InterfacePull(i) for i in intf.operands])
    else:
        data = nodes.InterfacePull(intf)

    ass_targets = assign_targets(ctx, targets, data, nodes.Variable)

    return intf, ass_targets


@node_visitor(ast.AsyncWith)
def asyncwith(node, ctx: Context):
    assigns = [visit_ast(i, ctx) for i in node.items]

    pydl_node = nodes.IntfBlock(intfs=[], stmts=[])
    ctx.pydl_block_closure.append(pydl_node)

    for intf, targets in assigns:
        if isinstance(intf, nodes.ConcatExpr):
            pydl_node.intfs.extend(intf.operands)
        else:
            pydl_node.intfs.append(intf)

        add_to_list(pydl_node.stmts, targets)

    for stmt in node.body:
        res_stmt = visit_ast(stmt, ctx)
        add_to_list(pydl_node.stmts, res_stmt)

    ctx.pydl_block_closure.pop()

    return pydl_node


class AsyncForContext:
    def __init__(self, intf, ctx):
        self.intf = intf
        self.ctx = ctx

    def __enter__(self):
        eot_name = '_eot'
        while eot_name in self.ctx.scope:
            eot_name = eot_name[:-1] + str(int(eot_name[-1]) + 1)

        self.ctx.scope[eot_name] = nodes.Variable(eot_name,
                                                  self.intf.dtype.eot)

        eot_init = nodes.Assign(nodes.ResExpr(self.intf.dtype.eot(0)),
                                self.ctx.ref(eot_name))

        eot_test = nodes.BinOpExpr(
            (self.ctx.ref(eot_name), nodes.ResExpr(self.intf.dtype.eot.max)),
            nodes.opc.NotEq)

        eot_load = nodes.Assign(
            nodes.SubscriptExpr(nodes.Component(self.intf.obj, 'data'),
                                nodes.ResExpr(-1)), self.ctx.ref(eot_name))

        intf_block = nodes.IntfBlock(intfs=[self.intf.obj], stmts=[eot_load])

        eot_loop_stmt = nodes.Loop(test=eot_test,
                                   stmts=[intf_block],
                                   multicycle=[])

        self.ctx.pydl_block_closure.append(intf_block)

        self.intf_block = intf_block

        return [eot_init, eot_loop_stmt]

    def __exit__(self, exception_type, exception_value, traceback):
        self.ctx.pydl_block_closure.append(self.intf_block)


@node_visitor(ast.AsyncFor)
def AsyncFor(node, ctx: Context):
    out_intf_ref = visit_ast(node.iter, ctx)

    with AsyncForContext(out_intf_ref, ctx) as stmts:
        targets = visit_ast(node.target, ctx)

        add_to_list(
            ctx.pydl_parent_block.stmts,
            assign_targets(ctx, targets,
                           nodes.Component(out_intf_ref.obj, 'data'),
                           nodes.Variable))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            add_to_list(ctx.pydl_parent_block.stmts, res_stmt)

        return stmts
