import ast

from pygears.typing import Uint
from pygears.util.utils import qrange

from . import hdl_types as ht
from .ast_data_utils import find_data_expression
from .ast_modifications import unroll_statements
from .ast_parse import parse_ast, parse_block
from .compile_snippets import enumerate_impl, qrange_mux_impl
from .hdl_utils import VisitError, add_to_list, find_for_target


def parse_for(node, module_data):

    res = find_data_expression(node.iter, module_data)

    names = find_for_target(node)

    if node.iter.func.id == 'range':
        return for_range(node, res, names, module_data)

    if node.iter.func.id == 'qrange':
        return for_qrange(node, res, names, module_data)

    if node.iter.func.id == 'enumerate':
        return for_enumerate(node, res, names, module_data)

    raise VisitError('Unsuported func in for loop')


def switch_reg_and_var(name, module_data):
    switch_name = f'{name}_switch'

    switch_reg = module_data.regs[name]
    module_data.variables[name] = ht.ResExpr(switch_reg.val)
    module_data.regs[switch_name] = switch_reg
    module_data.hdl_locals[switch_name] = ht.RegDef(switch_reg.val,
                                                    switch_name)
    module_data.regs.pop(name)
    module_data.hdl_locals.pop(name)
    if switch_name in module_data.variables:
        module_data.variables.pop(switch_name)


def add_reg(name, val, module_data):
    module_data.regs[name] = ht.ResExpr(val)
    module_data.hdl_locals[name] = ht.RegDef(val, name)


def add_variable(name, var, module_data):
    module_data.variables[name] = ht.OperandVal(var, 'v')
    module_data.hdl_locals[name] = var


def increment_reg(name, val=ast.Num(1), target=None):
    if not target:
        target = ast.Name(name, ast.Store())
    expr = ast.BinOp(ast.Name(name, ast.Load()), ast.Add(), val)
    return ast.Assign([target], expr)


def for_range(node, iter_args, target_names, module_data):
    if isinstance(iter_args, ht.ResExpr):
        _, stop, step = ht.ResExpr(iter_args.val.start), ht.ResExpr(
            iter_args.val.stop), ht.ResExpr(iter_args.val.step)
    else:
        _, stop, step = iter_args

    assert target_names[0] in module_data.regs, 'Loop iterator not registered'
    op1 = module_data.regs[target_names[0]]
    exit_cond = ht.BinOpExpr(
        (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop), '>=')

    hdl_node = ht.Loop(
        _in_cond=None, stmts=[], _exit_cond=exit_cond, multicycle=target_names)

    parse_block(hdl_node, node.body, module_data)

    target = node.target if len(target_names) == 1 else node.target.elts[0]
    add_to_list(
        hdl_node.stmts,
        parse_ast(
            increment_reg(target_names[0], val=step, target=target),
            module_data=module_data))

    return hdl_node


def for_qrange(node, iter_args, target_names, module_data):
    if isinstance(iter_args, ht.ResExpr):
        start, stop, step = ht.ResExpr(iter_args.val.start), ht.ResExpr(
            iter_args.val.stop), ht.ResExpr(iter_args.val.step)
    else:
        start, stop, step = iter_args

    is_start = True
    if isinstance(start, ht.ResExpr):
        is_start = start.val != 0

    assert target_names[0] in module_data.regs, 'Loop iterator not registered'
    op1 = module_data.regs[target_names[0]]
    exit_cond = ht.BinOpExpr(
        (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop), '>=')

    if is_start:
        switch_c = ht.OperandVal(
            ht.RegDef(op1, f'{target_names[0]}_switch'), 'next')
        exit_cond = ht.BinOpExpr((switch_c, stop), '>=')

    name = node.target.elts[-1].id
    var = ht.VariableDef(exit_cond, name)
    add_variable(name, var, module_data)
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
            module_data=module_data)

        loop_stmts = []
        for stmt in qrange_body:
            add_to_list(loop_stmts, parse_ast(stmt, module_data))

    parse_block(hdl_node, node.body, module_data)

    if is_start:
        hdl_node.stmts.extend(loop_stmts)
    else:
        target = node.target if len(target_names) == 1 else node.target.elts[0]
        add_to_list(
            hdl_node.stmts,
            parse_ast(
                increment_reg(target_names[0], val=step, target=target),
                module_data))

    return hdl_node


def qrange_impl(name, node, svnode, module_data):
    # implementation with flag register and mux

    # flag register
    flag_reg = 'qrange_flag'
    val = Uint[1](0)
    add_reg(flag_reg, val, module_data)

    svnode.multicycle.append(flag_reg)

    switch_reg = f'{name}_switch'
    svnode.multicycle.append(switch_reg)
    switch_reg_and_var(name, module_data)

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


def for_enumerate(node, iter_args, target_names, module_data):
    # assert target_names[
    #     0] in module_data.regs, 'Loop iterator not registered'
    assert target_names[
        -1] in module_data.in_intfs, 'Enumerate iterator not an interface'
    stop = iter_args[0]
    enum_target = node.iter.args[0].id

    if target_names[0] in module_data.regs:
        return registered_enumerate(node, target_names, stop, enum_target,
                                    module_data)

    return comb_enumerate(node, target_names, stop, enum_target, module_data)


def registered_enumerate(node, target_names, stop, enum_target, module_data):
    op1 = module_data.regs[target_names[0]]
    exit_cond = ht.BinOpExpr(
        (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop), '>=')

    hdl_node = ht.Loop(
        _in_cond=None, stmts=[], _exit_cond=exit_cond, multicycle=target_names)

    snip = enumerate_impl(target_names[0], target_names[1], enum_target,
                          range(stop.val))
    enumerate_body = ast.parse(snip).body

    for stmt in enumerate_body:
        add_to_list(hdl_node.stmts, parse_ast(stmt, module_data))

    parse_block(hdl_node, node.body, module_data)

    target = node.target if len(target_names) == 1 else node.target.elts[0]
    add_to_list(
        hdl_node.stmts,
        parse_ast(
            increment_reg(target_names[0], val=ht.ResExpr(1), target=target),
            module_data))

    return hdl_node


def comb_enumerate(node, target_names, stop, enum_target, module_data):
    hdl_node = ht.ContainerBlock(stmts=[])

    hdl_node.break_func = node.break_func
    for stmt in node.hdl_stmts:
        add_to_list(hdl_node.stmts, parse_ast(stmt, module_data))

    for i, last in qrange(stop.val):
        py_stmt = f'{target_names[0]} = Uint[bitw({stop.val})]({i}); {target_names[1]} = {enum_target}{i}'
        stmts = ast.parse(py_stmt).body + node.body

        unrolled = unroll_statements(module_data, stmts, i, target_names, last)

        parse_block(hdl_node, unrolled, module_data)

    return hdl_node
