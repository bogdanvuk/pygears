import typing
from . import Context, GearContext, FuncContext, Function, Submodule, ir, ir_utils, node_visitor, visit_ast, visit_block
from ..debug import print_func_parse_intro
from pygears import Intf, reg
from pygears.typing import typeof, Bool, Uint
from pygears.core.partial import combine_arg_kwds, extract_arg_kwds
from pygears.core.port import HDLConsumer, HDLProducer


def form_gear_args(args, kwds, func):
    kwd_args, kwds_only = extract_arg_kwds(kwds, func)
    args_only = combine_arg_kwds(args, kwd_args, func)

    return args_only, kwds_only


class UsedVarVisitor(ir_utils.IrExprVisitor):
    def __init__(self, used):
        self.used = used

    def visit_Name(self, node):
        if node.ctx == 'load':
            self.used.add(node.name)


class UsedVarStmtVisitor(ir_utils.IrVisitor):
    def __init__(self):
        super().__init__()
        self.used = set()

    def Expr(self, node):
        UsedVarVisitor(self.used).visit(node)


# TODO: Make it work with multiple target assignements
class UnusedVarCleanup(ir_utils.IrRewriter):
    def __init__(self, used, ctx):
        super().__init__()
        self.used = used
        self.ctx = ctx

    def AssignValue(self, node):
        if not isinstance(node.target, ir.Name):
            return node

        if node.target.name == '_state':
            # TODO: Find a better way of detecting whether state register is not needed
            # If we are getting rid of state register
            if '_rst_cond' in self.ctx.scope:
                state_en = ir.AssignValue(self.ctx.ref('_state_en'), ir.res_true)
                rst_cond = ir.AssignValue(ir.SubscriptExpr(self.ctx.ref('_rst_cond'), node.val),
                                          ir.res_true)
                return [state_en, rst_cond]
            else:
                return node

        if node.target.name in self.used or (isinstance(self.ctx, GearContext)
                                             and node.target.name in self.ctx.intfs):
            return node

        if node.target.name in self.ctx.scope:
            del self.ctx.scope[node.target.name]

        return None


def removed_unused_vars(node, ctx):
    # TODO: This part is only for the cleanup of the whole module with inferred
    # states. Find a better way to implement this if statement
    if isinstance(ctx, GearContext):
        used = set()
        for state in node.stmts[0].branches:
            v = UsedVarStmtVisitor()
            for stmt in state.stmts:
                v.visit(stmt)

            used.update(v.used)

        if len(node.stmts[0].branches) == 1 and '_state' not in used:
            node.stmts = node.stmts[0].branches[0].stmts

            ctx.scope['_state_en'] = ir.Variable('_state_en', dtype=Bool)
            state_type = ctx.scope['_state'].dtype
            state_num = int(state_type.max) + 1
            ctx.scope['_rst_cond'] = ir.Variable('_rst_cond', dtype=Uint[state_num])
            node.stmts.insert(0, ir.AssignValue(ctx.ref('_state_en'), ir.res_false))
            del ctx.scope['_state']

            # TODO: Why can't we just do this? Default value extraction in
            # svcompile creates a problem. Run "test_double_loop"
            # node.stmts.insert(0, ir.AssignValue(ctx.ref('_rst_cond'), ir.ResExpr(ctx.scope['_rst_cond'].dtype(0))))

            for s in range(state_num):
                node.stmts.insert(
                    0,
                    ir.AssignValue(ir.SubscriptExpr(
                        ctx.ref('_rst_cond'), ir.ResExpr(state_type(s))),
                        ir.res_false))

            used.update(['_state_en', '_rst_cond'])

        return UnusedVarCleanup(used, ctx).visit(node)
    else:
        v = UsedVarStmtVisitor()
        v.visit(node)
        return UnusedVarCleanup(v.used, ctx).visit(node)


class ComplexityExplorer(ir_utils.IrExprVisitor):
    def __init__(self):
        self.operations = 0
        self.names = 0

    def visit_Name(self, node):
        self.names += 1

    def visit_BinOpExpr(self, node):
        self.operations += 1
        super().visit_BinOpExpr(node)

    def visit_ConditionalExpr(self, node):
        self.operations += 1
        super().visit_ConditionalExpr(node)


# TODO: Should we use Inliner from passes/inline_cfg?
class Inliner(ir_utils.IrExprRewriter):
    def __init__(self, forwarded):
        self.forwarded = forwarded

    def visit_Name(self, node):
        if ((node.name not in self.forwarded) or (node.ctx != 'load')):
            return None

        val = self.forwarded[node.name]

        if isinstance(val, ir.ResExpr) and getattr(val.val, 'unknown', False):
            return node

        return val


def should_inline(func_ir, func_ctx, args):
    if len(func_ir.stmts) > 1:
        return False

    s = func_ir.stmts[0]

    if not isinstance(s, ir.FuncReturn):
        return False

    v = ComplexityExplorer()
    v.visit(s.expr)

    if v.operations <= 2 and v.names <= len(args):
        return True

    return False


def inline_expr(func_ir, func_ctx, args):
    s = func_ir.stmts[-1]
    return Inliner(args).visit(s.expr)


def parse_func_call(func: typing.Callable, args, kwds, ctx: Context):
    ctx_stack = reg['hls/ctx']

    uniqueid = ''
    if isinstance(ctx, FuncContext):
        uniqueid = ctx.funcref.name

    uniqueid += str(len(ctx_stack[0].functions))

    funcref = Function(func, args, kwds, uniqueid=uniqueid)

    if funcref not in ctx_stack[0].functions:
        func_ctx = FuncContext(funcref, args, kwds)
        print_func_parse_intro(func, funcref.ast)
        reg['hls/ctx'].append(func_ctx)
        func_ir = visit_ast(funcref.ast, func_ctx)
        reg['hls/ctx'].pop()
        func_ir = removed_unused_vars(func_ir, func_ctx)
        ctx_stack[0].functions[funcref] = (func_ir, func_ctx)
    else:
        (func_ir, func_ctx) = ctx_stack[0].functions[funcref]
        funcref_list = list(ctx_stack[0].functions.keys())
        funcref.uniqueid = funcref_list[funcref_list.index(funcref)].uniqueid

    args = func_ctx.argdict(args, kwds)

    if not should_inline(func_ir, func_ctx, args):
        return ir.FunctionCall(operands=list(args.values()),
                               ret_dtype=func_ctx.ret_dtype,
                               name=funcref.name)
    else:
        return inline_expr(func_ir, func_ctx, args)


def create_in_intf(i, ctx):
    p = i.consumers[-1]
    intf_name = f'{p.gear.basename}_{p.basename}'
    # p.producer.source(HDLProducer())
    ir_intf = ir.Variable(intf_name, ir.IntfType[p.producer.dtype, ir.IntfType.iout])
    ctx.scope[intf_name] = ir_intf
    return ctx.ref(intf_name)


def create_out_intf(p, ctx):
    intf_name = f'{p.gear.basename}_{p.basename}'
    ir_intf = ir.Variable(intf_name, ir.IntfType[p.consumer.dtype, ir.IntfType.iin])
    ctx.scope[intf_name] = ir_intf
    p.consumer.connect(HDLConsumer())
    return ctx.ref(intf_name)


def call_gear(func, args, kwds, ctx: Context):
    local_in = []
    for i, a in enumerate(args):
        if typeof(a.dtype, ir.IntfType):
            if not isinstance(a, ir.Name):
                raise Exception(f'Expressions with interfaces not yet supported')

            intf = Intf(a.dtype.dtype)
            for p in ctx.gear.in_ports:
                if p.basename == a.name:
                    intf.source(p)
                    break
            else:
                raise Exception(f'Declaring free interfaces in async gears not yet supported')
        else:
            intf = Intf(a.dtype)
            intf.source(HDLProducer())

        local_in.append(intf)

    if not all(isinstance(node, ir.ResExpr) for node in kwds.values()):
        raise Exception("Not supproted")

    reg['gear/exec_context'] = 'compile'
    outputs = func(*local_in, **{k: v.val for k, v in kwds.items()})
    reg['gear/exec_context'] = 'hls'

    if isinstance(outputs, tuple):
        gear_inst = outputs[0].producer.gear
    else:
        gear_inst = outputs.producer.gear

    in_ports = []
    for a, i in zip(args, local_in):
        if typeof(a.dtype, ir.IntfType):
            in_ports.append(a)
            continue

        in_ports.append(create_in_intf(i, ctx))

    stmts = []
    for a, intf in zip(args, in_ports):
        if a == intf:
            continue

        stmts.append(ir.AssignValue(ir.Component(intf, 'data'), a))

    # TODO: Hack! This functionality needs to be rewriten to resemble the way
    # hierarchical modules work. This only works if ccat is automatically
    # placed in front of a gear.
    in_gear_inst = local_in[0].consumers[-1].gear
    if in_gear_inst is not gear_inst:
        ccat_out = create_out_intf(in_gear_inst.out_ports[0], ctx)
        ctx.submodules.append(Submodule(in_gear_inst, in_ports, [ccat_out]))

        in_ports = [ccat_out]

    out_ports = []
    for p in gear_inst.out_ports:
        out_ports.append(create_out_intf(p, ctx))

    ctx.submodules.append(Submodule(gear_inst, in_ports, out_ports))

    if len(out_ports) == 1:
        return ctx.ref(out_ports[0].name), stmts
    else:
        return ir.TupleExpr(tuple(ctx.ref(p.name) for p in out_ports)), stmts
