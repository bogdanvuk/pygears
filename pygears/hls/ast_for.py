import ast
from functools import reduce

from pygears.typing import Uint, Bool, Int, bitw
from pygears.util.utils import qrange

from .ast_modifications import unroll_statements
from .ast_parse import parse_ast, parse_block, parse_node
from .ast_call import parse_func_args
from .compile_snippets import enumerate_impl, qrange_mux_impl
from .hls_expressions import (BinOpExpr, BreakExpr, OperandVal, RegDef,
                              ResExpr, VariableDef, VariableStmt, and_expr,
                              create_oposite, or_expr, ConcatExpr)
from .pydl_types import Block, CombBlock, IfBlock, Loop
from .utils import VisitError, add_to_list, find_for_target


@parse_node(ast.For)
def parse_for(node, module_data):
    names = find_for_target(node)

    if node.iter.func.id in ('range', 'qrange', 'enumerate'):
        func_args = parse_func_args(node.iter.args, module_data)

        if node.iter.func.id == 'enumerate':
            return for_enumerate(node,
                                 (ResExpr(len(func_args[0])), func_args[0]),
                                 names, module_data)

        if len(func_args) == 1:
            start = ResExpr(func_args[0].dtype(0))
            stop = func_args[0]
            step = ast.Num(1)
        else:
            start = func_args[0]
            stop = func_args[1]
            step = ast.Num(1) if len(func_args) == 2 else func_args[2]

        if node.iter.func.id == 'range':
            return for_range(node, (start, stop, step), names, module_data)

        if node.iter.func.id == 'qrange':
            return for_qrange(node, (start, stop, step), names, module_data)

    raise VisitError('Unsuported func in for loop')


def switch_reg_and_var(name, module_data):
    switch_name = f'{name}_switch'

    switch_reg = module_data.regs[name]
    module_data.variables[name] = VariableDef(switch_reg.val, name)
    module_data.regs[switch_name] = switch_reg
    module_data.hdl_locals[switch_name] = RegDef(switch_reg.val, switch_name)
    module_data.regs.pop(name)
    module_data.hdl_locals[name] = module_data.variables[name]
    if switch_name in module_data.variables:
        module_data.variables.pop(switch_name)


def add_reg(name, val, module_data):
    module_data.regs[name] = ResExpr(val)
    module_data.hdl_locals[name] = RegDef(val, name)


def add_variable(name, var, module_data):
    module_data.variables[name] = OperandVal(var, 'v')
    module_data.hdl_locals[name] = var


def increment_reg(name, val=ast.Num(1), target=None):
    if not target:
        target = ast.Name(name, ast.Store())
    expr = ast.BinOp(ast.Name(name, ast.Load()), ast.Add(), val)
    return ast.Assign([target], expr)


def for_range(node, iter_args, target_names, module_data):
    if isinstance(iter_args, ResExpr):
        _, stop, step = ResExpr(iter_args.val.start), ResExpr(
            iter_args.val.stop), ResExpr(iter_args.val.step)
    else:
        _, stop, step = iter_args

    # TODO: loop iterator size according to range
    assert target_names[0] in module_data.regs, 'Loop iterator not registered'
    op1 = module_data.regs[target_names[0]]
    exit_cond = BinOpExpr(
        (OperandVal(RegDef(op1, target_names[0]), 'next'), stop), '>=')

    hdl_node = Loop(_in_cond=None,
                    stmts=[],
                    _exit_cond=exit_cond,
                    multicycle=target_names)

    parse_block(hdl_node, node.body, module_data)

    target = node.target if len(target_names) == 1 else node.target.elts[0]
    add_to_list(
        hdl_node.stmts,
        parse_ast(increment_reg(target_names[0], val=step, target=target),
                  module_data=module_data))

    return hdl_node


def for_qrange(node, iter_args, target_names, module_data):
    if isinstance(iter_args, ResExpr):
        start, stop, step = ResExpr(iter_args.val.start), ResExpr(
            iter_args.val.stop), ResExpr(iter_args.val.step)
    else:
        start, stop, step = iter_args

    is_start = True
    if isinstance(start, ResExpr):
        is_start = start.val != 0

    assert target_names[0] in module_data.regs, 'Loop iterator not registered'
    op1 = module_data.regs[target_names[0]]
    exit_cond = BinOpExpr(
        (OperandVal(RegDef(op1, target_names[0]), 'next'), stop), '>=')

    if is_start:
        switch_c = OperandVal(RegDef(op1, f'{target_names[0]}_switch'), 'next')
        exit_cond = BinOpExpr((switch_c, stop), '>=')

    name = node.target.elts[-1].id
    var = VariableDef(exit_cond, name)
    add_variable(name, var, module_data)

    module_data.hdl_locals[target_names[0]] = op1
    stmts = [VariableStmt(var, exit_cond)]
    exit_cond = OperandVal(var, 'v')

    hdl_node = Loop(_in_cond=None,
                    stmts=stmts,
                    _exit_cond=exit_cond,
                    multicycle=target_names)

    if is_start:
        qrange_init, qrange_body = qrange_impl(name=target_names[0],
                                               node=node,
                                               svnode=hdl_node,
                                               module_data=module_data)

        # loop_stmts = []
        # for stmt in qrange_body:
        #     add_to_list(loop_stmts, parse_ast(stmt, module_data))

    parse_block(hdl_node, node.body, module_data)

    if is_start:
        # init_stmts = [parse_ast(stmt, module_data) for stmt in qrange_init]
        hdl_node.stmts = qrange_init + hdl_node.stmts + qrange_body
    else:
        target = node.target if len(target_names) == 1 else node.target.elts[0]
        add_to_list(
            hdl_node.stmts,
            parse_ast(increment_reg(target_names[0], val=step, target=target),
                      module_data))

    module_data.hdl_locals.pop(name)
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
    # args = []
    # for arg in node.iter.args:
    #     try:
    #         args.append(arg.id)
    #     except AttributeError:
    #         args.append(arg.args[0].id)
    args = [parse_ast(a, module_data) for a in node.iter.args]

    if len(args) == 1:
        args.insert(0, ResExpr(Uint[1](0)))  # start
    if len(args) == 2:
        args.append(ResExpr(Uint[1](1)))  # step

    from .ast_assign import assign_variable, assign_reg
    init_stmt = assign_variable(name, module_data, None, args[0])

    start_snip = f"""if {flag_reg}:
    {name} = {switch_reg}"""
    start_stmt = parse_ast(ast.parse(start_snip).body[0], module_data)

    loop_incr_stmt = assign_reg(
        switch_reg, module_data, None,
        BinOpExpr((OperandVal(module_data.variables[name], 'v'), args[2]),
                  '+'))

    loop_switch_stmt = assign_reg(flag_reg, module_data, None,
                                  ResExpr(Bool(True)))

    return [init_stmt, start_stmt], [loop_incr_stmt, loop_switch_stmt]


#     loop_snip = f"""{switch_reg} = {name} + {args[2]}
# {flag_reg} = True"""

#     return [ast_init] + ast.parse(start_snip).body, ast.parse(loop_snip).body


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
    exit_cond = BinOpExpr(
        (OperandVal(RegDef(op1, target_names[0]), 'next'), stop), '>=')

    hdl_node = Loop(_in_cond=None,
                    stmts=[],
                    _exit_cond=exit_cond,
                    multicycle=target_names)

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
            increment_reg(target_names[0], val=ResExpr(1), target=target),
            module_data))

    return hdl_node


def comb_enumerate(node, target_names, stop, enum_target, module_data):
    pydl_node = CombBlock(stmts=[])
    pydl_node.break_cond = []
    pydl_node.loop_iter_in_cond = []

    reg_name = node.break_func['reg']
    init_reg_stmt = ast.parse(
        f"{reg_name} = Uint[{node.break_func['length']}](0)").body[0]
        # f"{reg_name} = Uint[{bitw(node.break_func['length']-1)}](0)").body[0]
    add_to_list(pydl_node.stmts, parse_ast(init_reg_stmt, module_data))
    module_data.hdl_locals[reg_name].en_cond = 1

    for i, last in qrange(stop.val):
        py_stmt = (f'{target_names[0]} = Uint[bitw({stop.val-1})]({i}); '
                   f'{target_names[1]} = {enum_target}{i}')
        stmts = ast.parse(py_stmt).body + node.body

        unrolled = unroll_statements(module_data, stmts, i, target_names, last)

        parse_block(pydl_node, unrolled, module_data)

        break_comb_loop(pydl_node, module_data, reg_name)

    assign_reg_stmt = ast.parse(f'{reg_name} = {reg_name}').body[0]
    reg_dflt_block = IfBlock(_in_cond=create_oposite(
        reduce(or_expr, pydl_node.loop_iter_in_cond, None)),
                             stmts=[parse_ast(assign_reg_stmt, module_data)])
    pydl_node.stmts.append(reg_dflt_block)
    return pydl_node


def find_break_path(node, break_num, scope, found_num=0):
    found_num = found_num
    for stmt in node.stmts:
        if isinstance(stmt, Block):
            found_num = find_break_path(stmt, break_num, scope, found_num)
            if found_num == (break_num + 1):
                break
        elif isinstance(stmt, BreakExpr):
            found_num += 1

    if found_num == (break_num + 1):
        if isinstance(node, Block):
            scope.append(node)

    return found_num


def break_comb_loop(loop_to_break, module_data, reg_name):
    # current loop iteration
    break_num = len(loop_to_break.break_cond)

    # all sub conditions that lead to break
    scope = []
    find_break_path(loop_to_break, break_num, scope)
    sub_conds = [
        block.in_cond for block in scope
        if hasattr(block, 'in_cond') and block.in_cond is not None
    ]

    # added reg. condition in case inputs change
    loop_cond_stmt = ast.parse(
        f'({reg_name} == 0) or {reg_name}[{break_num}]').body[0]
    loop_reg_cond = parse_ast(loop_cond_stmt.value, module_data)
    sub_conds.append(loop_reg_cond)

    # merged in condition for current iteration
    in_cond = create_oposite(reduce(and_expr, sub_conds, None))

    if loop_to_break.break_cond:
        break_conds = reduce(and_expr,
                             loop_to_break.break_cond + [loop_reg_cond], None)
    else:
        break_conds = loop_reg_cond
        loop_to_break.break_cond = []

    assert scope[-1] == loop_to_break
    if_block = scope[-2]
    if_block._in_cond = and_expr(if_block._in_cond, break_conds)

    loop_to_break.break_cond.append(in_cond)
    loop_to_break.loop_iter_in_cond.append(if_block.in_cond)

    # register current loop iteration
    loop_stmt = parse_ast(
        ast.parse(f'{reg_name}[{break_num}] = 1').body[0], module_data)
    if_block.stmts.insert(0, loop_stmt)


@parse_node(ast.ListComp)
def parse_list_comp(node, module_data):
    comprehension = node.generators[0]
    rng = parse_ast(comprehension.iter, module_data)
    var = comprehension.target.id
    concat = []
    if rng.val.start < 0 or rng.val.stop < 0:
        iter_type = type(Int(max(abs(rng.val.start), abs(rng.val.stop))))
    else:
        iter_type = type(Uint(max(rng.val.start, rng.val.stop)))

    for i in rng.val:
        module_data.hdl_locals[var] = ResExpr(iter_type(i))
        concat.append(parse_ast(node.elt, module_data))

    return ConcatExpr(concat)
