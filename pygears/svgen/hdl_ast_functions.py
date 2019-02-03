import ast
from functools import reduce

import hdl_types as ht
from compile_snippets import enumerate_impl, qrange_mux_impl
from pygears.typing import Int, Tuple, Uint, typeof


def switch_reg_and_var(name, regs, variables, hdl_locals):
    switch_name = f'{name}_switch'

    switch_reg = regs[name]
    variables[name] = ht.ResExpr(switch_reg.val)
    regs[switch_name] = switch_reg
    hdl_locals[switch_name] = ht.RegDef(switch_reg.val, switch_name)
    regs.pop(name)
    hdl_locals.pop(name)
    if switch_name in variables:
        variables.pop(switch_name)
    return


def add_reg(name, val, regs, hdl_locals):
    regs[name] = ht.ResExpr(val)
    hdl_locals[name] = ht.RegDef(val, name)


def add_variable(name, var, variables, hdl_locals):
    variables[name] = ht.OperandVal(var, 'v')
    hdl_locals[name] = var


def increment_reg(name, val=ast.Num(1), target=None):
    if not target:
        target = ast.Name(name, ast.Store())
    expr = ast.BinOp(ast.Name(name, ast.Load()), ast.Add(), val)
    return ast.Assign([target], expr)


def Call_len(arg, **kwds):
    return ht.ResExpr(len(arg.dtype))


def Call_print(arg, **kwds):
    pass


def Call_int(arg, **kwds):
    # ignore cast
    return arg


def Call_range(*arg, **kwds):
    if len(arg) == 1:
        start = ht.ResExpr(arg[0].dtype(0))
        stop = arg[0]
        step = ast.Num(1)
    else:
        start = arg[0]
        stop = arg[1]
        step = ast.Num(1) if len(arg) == 2 else arg[2]

    return start, stop, step


def Call_qrange(*arg, **kwds):
    return Call_range(*arg)


def Call_all(arg, **kwds):
    return ht.ArrayOpExpr(arg, '&')


def max_expr(op1, op2):
    op1_compare = op1
    op2_compare = op2
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = ht.CastExpr(op1, Int[int(op1.dtype) + 1])
    if signed and typeof(op2.dtype, Uint):
        op2_compare = ht.CastExpr(op2, Int[int(op2.dtype) + 1])

    cond = ht.BinOpExpr((op1_compare, op2_compare), '>')
    return ht.ConditionalExpr(cond=cond, operands=(op1, op2))


def Call_max(*arg, **kwds):
    if len(arg) == 1:
        arg = arg[0]

        assert isinstance(arg, ht.IntfExpr), 'Not supported yet...'
        assert typeof(arg.dtype, Tuple), 'Not supported yet...'

        op = []
        for f in arg.dtype.fields:
            op.append(ht.AttrExpr(arg, [f]))

        return reduce(max_expr, op)

    else:
        return reduce(max_expr, arg)


def Call_enumerate(arg, **kwds):
    return ht.ResExpr(len(arg)), arg


def Call_sub(*arg, **kwds):
    assert not arg, 'Sub should be called without arguments'
    value = kwds['value']
    return ht.CastExpr(value, cast_to=value.dtype.sub())


def For_range(ast_visitor, node, iter_args, target_names):
    if isinstance(iter_args, ht.ResExpr):
        start, stop, step = ht.ResExpr(iter_args.val.start), ht.ResExpr(
            iter_args.val.stop), ht.ResExpr(iter_args.val.step)
    else:
        start, stop, step = iter_args

    assert target_names[0] in ast_visitor.regs, 'Loop iterator not registered'
    op1 = ast_visitor.regs[target_names[0]]
    exit_cond = ht.BinOpExpr(
        (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop), '>=')

    hdl_node = ht.Loop(
        _in_cond=None, stmts=[], _exit_cond=exit_cond, multicycle=target_names)

    ast_visitor.visit_block(hdl_node, node.body)

    target = node.target if len(target_names) == 1 else node.target.elts[0]
    hdl_node.stmts.append(
        ast_visitor.visit(
            increment_reg(target_names[0], val=step, target=target)))

    return hdl_node


def qrange_impl(name, node, svnode, rng, regs, variables, hdl_locals):
    # implementation with flag register and mux

    # flag register
    flag_reg = 'qrange_flag'
    val = Uint[1](0)
    add_reg(flag_reg, val, regs, hdl_locals)

    svnode.multicycle.append(flag_reg)

    switch_reg = f'{name}_switch'
    svnode.multicycle.append(switch_reg)
    switch_reg_and_var(name, regs, variables, hdl_locals)

    # impl.
    args = []
    for arg in node.iter.args:
        try:
            args.append(arg.id)
        except AttributeError:
            args.append(arg.args[0].id)
    if len(args) == 1:
        args.insert(0, '0')  # start
    if len(args) == 2:
        args.append('1')  # step

    snip = qrange_mux_impl(name, switch_reg, flag_reg, args)
    return ast.parse(snip).body


def For_qrange(ast_visitor, node, iter_args, target_names):
    if isinstance(iter_args, ht.ResExpr):
        start, stop, step = ht.ResExpr(iter_args.val.start), ht.ResExpr(
            iter_args.val.stop), ht.ResExpr(iter_args.val.step)
    else:
        start, stop, step = iter_args

    is_start = True
    if isinstance(start, ht.ResExpr):
        is_start = start.val != 0

    assert target_names[0] in ast_visitor.regs, 'Loop iterator not registered'
    op1 = ast_visitor.regs[target_names[0]]
    exit_cond = ht.BinOpExpr(
        (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop), '>=')

    if is_start:
        x = ht.OperandVal(ht.RegDef(op1, f'{target_names[0]}_switch'), 'next')
        exit_cond = ht.BinOpExpr((x, stop), '>=')

    name = node.target.elts[-1].id
    var = ht.VariableDef(exit_cond, name)
    add_variable(name, var, ast_visitor.variables, ast_visitor.hdl_locals)
    stmts = [ht.VariableStmt(var, exit_cond)]
    exit_cond = ht.OperandVal(var, 'v')

    hdl_node = ht.Loop(
        _in_cond=None,
        stmts=stmts,
        _exit_cond=exit_cond,
        multicycle=target_names)

    if is_start:
        qrange_body = qrange_impl(
            name=target_names[0],
            node=node,
            svnode=hdl_node,
            rng=[start, stop, step],
            regs=ast_visitor.regs,
            variables=ast_visitor.variables,
            hdl_locals=ast_visitor.hdl_locals)

        loop_stmts = []
        for stmt in qrange_body:
            loop_stmts.append(ast_visitor.visit(stmt))

    ast_visitor.visit_block(hdl_node, node.body)

    if is_start:
        hdl_node.stmts.extend(loop_stmts)
    else:
        target = node.target if len(target_names) == 1 else node.target.elts[0]
        hdl_node.stmts.append(
            ast_visitor.visit(
                increment_reg(target_names[0], val=step, target=target)))

    return hdl_node


def For_enumerate(ast_visitor, node, iter_args, target_names):
    assert target_names[0] in ast_visitor.regs, 'Loop iterator not registered'
    assert target_names[
        -1] in ast_visitor.in_intfs, 'Enumerate iterator not an interface'
    stop = iter_args[0]

    op1 = ast_visitor.regs[target_names[0]]
    exit_cond = ht.BinOpExpr(
        (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop), '>=')

    hdl_node = ht.Loop(
        _in_cond=None, stmts=[], _exit_cond=exit_cond, multicycle=target_names)

    enum_target = node.iter.args[0].id
    snip = enumerate_impl(target_names[0], target_names[1], enum_target,
                          range(stop.val))
    enumerate_body = ast.parse(snip).body

    for stmt in enumerate_body:
        hdl_node.stmts.append(ast_visitor.visit(stmt))

    ast_visitor.visit_block(hdl_node, node.body)

    target = node.target if len(target_names) == 1 else node.target.elts[0]
    hdl_node.stmts.append(
        ast_visitor.visit(
            increment_reg(target_names[0], val=ht.ResExpr(1), target=target)))

    return hdl_node
