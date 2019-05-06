import ast
import copy

from pygears.typing import Uint

from .ast_parse import parse_ast
from .hls_expressions import (OperandVal, RegDef, RegNextStmt, ResExpr,
                              create_oposite)
from .pydl_types import (ContainerBlock, IfBlock, IntfBlock, IntfLoop, Loop,
                         Module, Yield)
from .utils import add_to_list

FLAG_NAME = 'pipeline_flag'


def pipeline_ast(pydl_ast, module_data):
    # this optimization can only be used for the following situation:
    # two blocks: async for/with is first, yield is second
    # pipeline optimization merges the operations so that the yield and
    # data fetching can be done in the same clk cycle

    # the optimization is performed in the following way:
    # original code:
    #     register initialization
    #     async ...
    #        some stmts
    #     yield
    # optimized code:
    #    register initialization
    #    while True:
    #        if done:
    #            yield
    #            try:
    #                non blocking async
    #                some stmts
    #            except QueueEmpty:
    #                register initialization
    #        else:
    #            async ..
    #               some stmts

    assert len(pydl_ast.stmts) == 2 and isinstance(
        pydl_ast.stmts[0], (IntfBlock, IntfLoop)) and isinstance(
            pydl_ast.stmts[-1],
            Yield), 'Pipeline optimization not supported...'

    flag_val = ResExpr(val=Uint[1](0))

    # add pipeline reg
    module_data.regs[FLAG_NAME] = flag_val
    module_data.hdl_locals[FLAG_NAME] = RegDef(val=flag_val, name=FLAG_NAME)

    # create if/else for pipeline reg
    if_pipe_cond = OperandVal(
        op=module_data.hdl_locals[FLAG_NAME], context='reg')

    # if branch starts with yield + tries to get data
    if_block = IfBlock(_in_cond=if_pipe_cond, stmts=[pydl_ast.stmts[-1]])
    try_block = get_try_except(pydl_ast, module_data)
    if_block.stmts.append(try_block)

    # else branch is the same as original first stmt + flag is assigned
    else_block = IfBlock(
        _in_cond=create_oposite(if_pipe_cond), stmts=[pydl_ast.stmts[0]])
    py_stmt = ast.parse(f'{FLAG_NAME} = True').body[0]
    flag_stmt = parse_ast(py_stmt, module_data)
    else_block.stmts.append(flag_stmt)

    container_block = ContainerBlock(stmts=[if_block, else_block])

    # create while True loop
    true_cond = ResExpr(val=Uint[1](1))
    optimized_loop = Loop(
        _in_cond=true_cond,
        _exit_cond=create_oposite(true_cond),
        multicycle=True,
        stmts=[container_block])

    return Module(stmts=[optimized_loop])


def init_registers(module_data):
    stmts = []
    for reg, val in module_data.regs.items():
        init_stmt = RegNextStmt(reg=module_data.hdl_locals[reg], val=val)
        stmts.append(init_stmt)

    return stmts


def get_try_except(pydl_ast, module_data):
    intf = pydl_ast.stmts[0].intf

    except_part = IfBlock(
        _in_cond=create_oposite(intf), stmts=init_registers(module_data))

    # replace registers with their initial values
    try_stmts = replace_context(pydl_ast.stmts[0].stmts, module_data)

    intf_type = 'True' if isinstance(pydl_ast.stmts[0], IntfBlock) else 'eot'
    py_stmt = ast.parse(f'{FLAG_NAME} = {intf_type}').body[0]
    flag_stmt = parse_ast(py_stmt, module_data)
    try_stmts.append(flag_stmt)  # success so assign flag

    try_part = IntfBlock(intf=intf, stmts=try_stmts)

    return ContainerBlock(stmts=[try_part, except_part])


def replace_context(node, module_data):
    if isinstance(node, list):
        res = []
        for x in node:
            add_to_list(res, replace_context(x, module_data))
        return res

    node = copy.copy(node)
    if hasattr(node, 'stmts'):
        stmts = []
        for stmt in node.stmts:
            s = replace_context(stmt, module_data)
            add_to_list(stmts, s)
        node.stmts = stmts

    if hasattr(node, '_in_cond'):
        c = replace_context(node._in_cond, module_data)
        if isinstance(c, ResExpr) and not c.val:
            return None
        node._in_cond = c
    if hasattr(node, '_exit_cond'):
        node._exit_cond = replace_context(node._exit_cond, module_data)

    if isinstance(node, RegDef):
        return ResExpr(module_data.regs[node.name].val)  # return initial value

    if hasattr(node, 'val'):
        node.val = replace_context(node.val, module_data)
        return node

    if hasattr(node, 'operand'):
        node.operand = replace_context(node.operand, module_data)
        return node

    if hasattr(node, 'operands'):
        ops = []
        for op in node.operands:
            ops.append(replace_context(op, module_data))
        node.operands = ops
        return node

    if isinstance(node, OperandVal) and isinstance(node.op, RegDef):
        return ResExpr(
            module_data.regs[node.op.name].val)  # return initial value

    return node
