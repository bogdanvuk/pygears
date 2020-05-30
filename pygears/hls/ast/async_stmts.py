import ast
from . import Context, ir, node_visitor, visit_ast
from .cast import resolve_cast_func
from .utils import add_to_list
from .stmt import assign_targets


def is_target_id(node):
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


# TODO: Revisit cast_return, maybe it can be more general
from pygears.typing import typeof, Queue, Tuple, Array


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)
    if isinstance(arg_nodes, (list, tuple)):
        assert len(arg_nodes) == out_num
        input_vars = arg_nodes
    elif isinstance(arg_nodes, ir.TupleExpr):
        input_vars = arg_nodes.val
    elif isinstance(arg_nodes, ir.Name) and out_num > 1:
        var = arg_nodes.obj
        assert len(var.dtype) == out_num
        input_vars = []
        for i in range(len(var.dtype)):
            input_vars.append(
                ir.SubscriptExpr(val=arg_nodes, index=ir.ResExpr(i)))
    else:
        if out_num == 1:
            input_vars = [arg_nodes]
        else:
            assert isinstance(arg_nodes, ir.TupleExpr)
            input_vars = arg_nodes.val

    args = []
    for arg, intf in zip(input_vars, out_ports):
        port_t = intf.dtype
        # TODO: Let this be handled by typing.cast function for better error reporting
        if typeof(port_t, (Queue, Tuple, Array)):
            if isinstance(arg, ir.ConcatExpr) and arg.dtype != port_t:
                for i in range(len(arg.operands)):
                    if isinstance(arg.operands[i], ir.CastExpr) and (
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

    return ir.TupleExpr(args)


@node_visitor(ast.Yield)
def parse_yield(node, ctx):
    yield_expr = visit_ast(node.value, ctx)

    try:
        ret = cast_return(yield_expr, ctx.gear.out_ports)
    except TypeError as e:
        raise SyntaxError(
            f"{str(e)}\n    - when casting output value to the output type")

    if isinstance(ret, ir.TupleExpr):
        vals = ret.val
    else:
        vals = [ret]

    stmts = []
    for p, v in zip(ctx.out_ports, vals):
        stmts.append(ir.AssignValue(p, v))

        if len(ctx.out_ports) == 1:
            stmts.append(
                ir.ExprStatement(
                    ir.Await(exit_await=ir.Component(p, 'ready'))))
        else:
            stmts.append(
                ir.ExprStatement(
                    ir.Await(exit_await=ir.BinOpExpr((
                        ir.UnaryOpExpr(ir.Component(p, 'valid'), ir.opc.Not),
                        ir.Component(p, 'ready')), ir.opc.Or))))

    return stmts


@node_visitor(ast.withitem)
def withitem(node: ast.withitem, ctx: Context):
    intf = visit_ast(node.context_expr, ctx)
    targets = visit_ast(node.optional_vars, ctx)

    if isinstance(intf, ir.ConcatExpr):
        data = ir.ConcatExpr([
            ir.Await(ir.Component(i, 'data'),
                     in_await=ir.Component(i, 'valid')) for i in intf.operands
        ])
    else:
        data = ir.Await(ir.Component(intf, 'data'),
                        in_await=ir.Component(intf, 'valid'))

    ass_targets = assign_targets(ctx, targets, data, ir.Variable)

    return intf, ass_targets


@node_visitor(ast.AsyncWith)
def asyncwith(node, ctx: Context):
    assigns = [visit_ast(i, ctx) for i in node.items]

    intfs = []
    stmts = []
    for intf, targets in assigns:
        if isinstance(intf, ir.ConcatExpr):
            intfs.extend(intf.operands)
        else:
            intfs.append(intf)

        add_to_list(stmts, targets)

    for stmt in node.body:
        res_stmt = visit_ast(stmt, ctx)
        add_to_list(stmts, res_stmt)

    for i in intfs:
        stmts.append(ir.AssignValue(ir.Component(i, 'ready'), ir.res_true))

    return stmts


class AsyncForContext:
    def __init__(self, intf, ctx):
        self.intf = intf
        self.ctx = ctx

    def __enter__(self):
        eot_name = self.ctx.find_unique_name('_eot')
        data_name = self.ctx.find_unique_name('_data')

        intf_obj = self.intf.obj.val

        self.ctx.scope[eot_name] = ir.Variable(eot_name, intf_obj.dtype.eot)
        self.ctx.scope[data_name] = ir.Variable(data_name, intf_obj.dtype.data)

        eot_init = ir.AssignValue(
            self.ctx.ref(eot_name),
            ir.ResExpr(intf_obj.dtype.eot(0)),
        )

        eot_test = ir.BinOpExpr(
            (self.ctx.ref(eot_name), ir.ResExpr(intf_obj.dtype.eot.max)),
            ir.opc.NotEq)

        eot_load = ir.AssignValue(
            self.ctx.ref(eot_name),
            ir.SubscriptExpr(ir.Component(self.intf, 'data'), ir.ResExpr(-1)))

        data_load = ir.AssignValue(
            self.ctx.ref(data_name),
            ir.Await(ir.Component(self.intf, 'data'),
                     in_await=ir.Component(self.intf, 'valid')))

        eot_loop_stmt = ir.LoopBlock(test=eot_test,
                                     stmts=[data_load, eot_load])

        self.ctx.ir_block_closure.append(eot_loop_stmt)

        return [eot_init, eot_loop_stmt]

    def __exit__(self, exception_type, exception_value, traceback):
        loop = self.ctx.ir_block_closure.pop()
        loop.stmts.append(
            ir.AssignValue(ir.Component(self.intf, 'ready'), ir.res_true))


@node_visitor(ast.AsyncFor)
def AsyncFor(node, ctx: Context):
    out_intf_ref = visit_ast(node.iter, ctx)
    targets = visit_ast(node.target, ctx)

    with AsyncForContext(out_intf_ref, ctx) as stmts:
        add_to_list(
            ctx.ir_parent_block.stmts,
            assign_targets(ctx, targets, ir.Component(out_intf_ref, 'data'),
                           ir.Variable))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            add_to_list(ctx.ir_parent_block.stmts, res_stmt)

        return stmts


@node_visitor(ast.Await)
def _(node: ast.Await, ctx: Context):
    return ir.ExprStatement(
        ir.Await(in_await=ir.res_false, exit_await=ir.res_false))
