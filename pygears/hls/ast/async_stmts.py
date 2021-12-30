import ast
from . import Context, ir, node_visitor, visit_ast
from .cast import resolve_cast_func
from .stmt import assign_targets, extend_stmts
from ..ir_utils import is_intf_id


def is_target_id(node):
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


def merge_cond_alias_map(ir_node, ctx):
    alias_map = ctx.alias_map
    for n, v in ctx.closure_alias_maps[ir_node].items():
        if n in alias_map:
            if v is not alias_map[n] and v != alias_map[n]:
                alias_map[n] = ctx.ref(n)


# TODO: Revisit cast_return, maybe it can be more general
from pygears.typing import typeof, Queue, Tuple, Array


def cast_rec(node, t):
    if node == ir.ResExpr(None):
        return ir.ResExpr(ir.EmptyType[t]())
    elif node.dtype == t:
        return node
    elif typeof(node.dtype, ir.IntfType):
        # TODO: Do proper casting of interfaces
        return node
    elif not typeof(t, (Queue, Tuple, Array)):
        return resolve_cast_func(node, t)

    if isinstance(node, ir.ConcatExpr):
        ops = node.operands
    elif isinstance(node, ir.ResExpr):
        ops = [ir.ResExpr(v) for v in node.val]
    else:
        # TODO: Should this be done with indexing to ensure proper casting of fields?
        return node

    opout = []
    for i in range(len(ops)):
        opout.append(cast_rec(ops[i], t[i]))

    return ir.ConcatExpr(opout)


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)

    # TODO: Reconsider this: Can we have a type inference mechanism?
    if out_num == 0:
        raise TypeError(f"Function must have a return type defined!")

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
            input_vars.append(ir.SubscriptExpr(val=arg_nodes, index=ir.ResExpr(i)))
    else:
        if out_num == 1:
            input_vars = [arg_nodes]
        elif isinstance(arg_nodes, ir.TupleExpr):
            input_vars = arg_nodes.val
        elif isinstance(arg_nodes, ir.ConcatExpr):
            input_vars = arg_nodes.operands
        elif isinstance(arg_nodes, ir.ResExpr) and isinstance(arg_nodes.val, tuple):
            input_vars = [ir.ResExpr(v) for v in arg_nodes.val]
        else:
            breakpoint()
            raise Exception('Unsupported')

    args = []
    for arg, intf in zip(input_vars, out_ports):
        port_t = intf.dtype
        args.append(cast_rec(arg, port_t))

    return ir.TupleExpr(args)


@node_visitor(ast.Yield)
def parse_yield(node, ctx):
    yield_expr = visit_ast(node.value, ctx)

    try:
        ret = cast_return(yield_expr, ctx.gear.out_ports)
    except TypeError as e:
        raise SyntaxError(f"{str(e)}\n    - when casting output value to the output type")

    if isinstance(ret, ir.TupleExpr):
        vals = ret.val
    else:
        vals = [ret]

    if any(is_intf_id(v) for v in vals):
        return [ir.AssignValue(p, v) for p, v in zip(ctx.out_ports, vals)]

    stmts = []

    stmts.append(ir.Await('forward'))

    # Outputs values are offered in parallel. So first all outputs are declared
    # valid, and only then are all acknowledges awaited
    for p, v in zip(ctx.out_ports, vals):
        if isinstance(v, ir.ResExpr) and isinstance(v.val, ir.EmptyType):
            continue

        stmts.append(ir.AssignValue(ir.Component(p, 'data'), v))

    for p, v in zip(ctx.out_ports, vals):
        if isinstance(v, ir.ResExpr) and isinstance(v.val, ir.EmptyType):
            continue

        stmts.append(ir.Await(ir.Component(p, 'ready')))

    stmts.append(ir.Await('back'))

    return stmts


@node_visitor(ast.withitem)
def withitem(node: ast.withitem, ctx: Context):
    intf = visit_ast(node.context_expr, ctx)
    targets = visit_ast(node.optional_vars, ctx)

    if isinstance(intf, ir.ConcatExpr):
        data = ir.ConcatExpr([ir.Component(i, 'data') for i in intf.operands])
    else:
        data = ir.Component(intf, 'data')

    ass_targets = assign_targets(ctx, targets, data)

    return intf, ass_targets


@node_visitor(ast.AsyncWith)
def asyncwith(node, ctx: Context):
    assigns = [visit_ast(i, ctx) for i in node.items]

    intfs = []
    for intf, _ in assigns:
        if isinstance(intf, ir.ConcatExpr):
            intfs.extend(intf.operands)
        else:
            intfs.append(intf)

    for i in intfs:
        extend_stmts(ctx.ir_parent_block.stmts, ir.Await(ir.Component(i, 'valid')))

    for _, targets in assigns:
        extend_stmts(ctx.ir_parent_block.stmts, targets)

    # stmts = []
    for stmt in node.body:
        res_stmt = visit_ast(stmt, ctx)
        extend_stmts(ctx.ir_parent_block.stmts, res_stmt)
        # extend_stmts(stmts, res_stmt)

    # stmts.append(ir.Await('back'))
    extend_stmts(ctx.ir_parent_block.stmts, ir.Await('back'))
    for i in intfs:
        extend_stmts(
            ctx.ir_parent_block.stmts,
            ir.AssignValue(ir.Component(i, 'ready'), ir.res_true),
        )
        # stmts.append(ir.AssignValue(ir.Component(i, 'ready'), ir.res_true))

    # return stmts


class AsyncForContext:
    def __init__(self, intf, ctx):
        self.intf = intf
        self.ctx = ctx

    def __enter__(self):
        eot_name = self.ctx.find_unique_name('_eot')
        data_name = self.ctx.find_unique_name('_data')

        intf_type = self.intf.dtype.dtype

        self.ctx.scope[eot_name] = ir.Variable(eot_name, intf_type.eot)
        self.ctx.scope[data_name] = ir.Variable(data_name, intf_type.data)

        eot_init = ir.AssignValue(
            self.ctx.ref(eot_name),
            ir.ResExpr(intf_type.eot(0)),
        )

        eot_test = ir.BinOpExpr((self.ctx.ref(eot_name), ir.ResExpr(intf_type.eot.max)),
                                ir.opc.NotEq)

        eot_load = ir.AssignValue(self.ctx.ref(eot_name),
                                  ir.SubscriptExpr(ir.Component(self.intf, 'data'), ir.ResExpr(-1)))

        valid_await = ir.Await(ir.Component(self.intf, 'valid'))
        data_load = ir.AssignValue(self.ctx.ref(data_name), ir.Component(self.intf, 'data'))

        eot_loop_stmt = ir.LoopBlock(test=eot_test, stmts=[valid_await, data_load, eot_load])

        self.ctx.new_closure(eot_loop_stmt)

        return [eot_init, eot_loop_stmt]

    def __exit__(self, exception_type, exception_value, traceback):
        loop = self.ctx.closures.pop()

        loop.stmts.append(ir.Await('back'))
        loop.stmts.append(ir.AssignValue(ir.Component(self.intf, 'ready'), ir.res_true))
        merge_cond_alias_map(loop, self.ctx)


@node_visitor(ast.AsyncFor)
def AsyncFor(node, ctx: Context):
    out_intf_ref = visit_ast(node.iter, ctx)
    targets = visit_ast(node.target, ctx)

    with AsyncForContext(out_intf_ref, ctx) as stmts:
        extend_stmts(ctx.ir_parent_block.stmts,
                     assign_targets(ctx, targets, ir.Component(out_intf_ref, 'data')))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            extend_stmts(ctx.ir_parent_block.stmts, res_stmt)

        return stmts


@node_visitor(ast.Await)
def _(node: ast.Await, ctx: Context):
    if isinstance(node.value, ast.Call):
        res = visit_ast(node.value.func, ctx)
        from pygears.sim import clk
        if isinstance(res, ir.ResExpr):
            if res.val == clk:
                return [ir.Await('back'), ir.Await('forward')]
            elif res.val.__qualname__ == 'Intf.ready':
                intf = res.val.__self__
                for p in ctx.gear.out_ports:
                    if p.producer is intf:
                        break
                else:
                    breakpoint()

                return ir.Await(ir.Component(ctx.ref(p.basename), 'ready'))

    breakpoint()
