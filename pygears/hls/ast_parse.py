import ast
import itertools
from functools import singledispatch

from pygears.typing import Array, Int, Integer, Uint, Unit, typeof, Tuple
from pygears.core.util import get_function_context_dict

from . import hls_expressions as expr
from .hdl_arith import resolve_cast_func
from . import pydl_types as blocks
from .utils import (add_to_list, cast_return, eval_local_expression,
                    find_assign_target, find_data_expression,
                    find_name_expression, get_bin_expr, get_context_var,
                    intf_parse)


@singledispatch
def parse_ast(node, module_data):
    """Used by default. Called if no explicit function exists for a node."""
    for _, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    parse_ast(item, module_data)
        elif isinstance(value, ast.AST):
            parse_ast(value, module_data)


def parse_block(pydl_node, body, module_data):
    module_data.context.append(pydl_node)
    for stmt in body:
        res_stmt = parse_ast(stmt, module_data)
        add_to_list(pydl_node.stmts, res_stmt)

    module_data.context.pop()

    return pydl_node


@parse_ast.register(ast.AsyncFunctionDef)
def parse_async_func(node, module_data):
    pydl_node = blocks.Module(stmts=[])

    # initialization for register without explicit assign in code
    reg_names = list(module_data.regs.keys())
    assign_names = list(
        itertools.chain.from_iterable(
            find_assign_target(stmt) for stmt in node.body
            if isinstance(stmt, ast.Assign)))
    missing_reg = [name for name in reg_names if name not in assign_names]
    for name in missing_reg:
        module_data.hdl_locals[name] = expr.RegDef(module_data.regs[name],
                                                   name)

    return parse_block(pydl_node, node.body, module_data)


@parse_ast.register(ast.Expr)
def parse_expr(node, module_data):
    if isinstance(node.value, ast.Yield):
        return parse_yield(node.value, module_data)

    return parse_ast(node.value, module_data)


@parse_ast.register(ast.Return)
def parse_return(node, module_data):
    ret_expr = parse_ast(node.value, module_data)

    for func_block in reversed(module_data.context):
        if isinstance(func_block, blocks.Function):
            break
    else:
        raise Exception('Return found outside function')

    if func_block.ret_dtype:
        ret_expr = resolve_cast_func(func_block.ret_dtype, ret_expr)

    return expr.ReturnStmt(ret_expr)


@parse_ast.register(ast.IfExp)
def parse_ifexp(node, module_data):
    res = {
        field: find_data_expression(getattr(node, field), module_data)
        for field in ['test', 'body', 'orelse']
    }
    return expr.ConditionalExpr(operands=(res['body'], res['orelse']),
                                cond=res['test'])


@parse_ast.register(ast.Yield)
def parse_yield(node, module_data):
    if isinstance(node.value, ast.Tuple) and len(module_data.out_ports) > 1:
        ports = []
        yield_expr = [
            find_data_expression(item, module_data) for item in node.value.elts
        ]
        for i, val in enumerate(yield_expr):
            if not (isinstance(val, expr.ResExpr) and val.val is None):
                ports.append(list(module_data.out_ports.values())[i])
    else:
        yield_expr = parse_ast(node.value, module_data)
        ports = list(module_data.out_ports.values())
    stmts = []

    try:
        ret = cast_return(yield_expr, module_data.out_ports)
    except Exception as e:
        raise Exception('Output value incompatible with output type')

    add_to_list(stmts, ret)
    return blocks.Yield(stmts=stmts, ports=ports)


@parse_ast.register(ast.While)
def parse_while(node, module_data):
    test = find_data_expression(node.test, module_data)
    multi = []
    if isinstance(test, expr.ResExpr) and test.val:
        multi = True
    pydl_node = blocks.Loop(_in_cond=test,
                            stmts=[],
                            _exit_cond=expr.create_oposite(test),
                            multicycle=multi)

    return parse_block(pydl_node, node.body, module_data)


def find_subscript_expression(node, module_data):
    if not isinstance(node, ast.Subscript):
        return None

    # input interface as array ie din[x]
    name = node.value.id
    val_expr = get_context_var(name, module_data)
    stmts = []
    for i in range(len(val_expr)):
        py_stmt = f'if {node.slice.value.id} == {i}: {name} = {name}{i}'
        snip = ast.parse(py_stmt).body[0]
        add_to_list(stmts, parse_ast(snip, module_data))
    return stmts


@parse_ast.register(ast.AsyncFor)
def parse_asyncfor(node, module_data):
    intf = find_name_expression(node.iter, module_data)
    scope, loop_intf = intf_parse(intf=intf, target=node.target)

    module_data.hdl_locals.update(scope)

    pydl_node = blocks.IntfLoop(intf=loop_intf, stmts=[], multicycle=scope)

    assign_stmts = find_subscript_expression(node.iter, module_data)
    parse_block(pydl_node, node.body, module_data)

    if not assign_stmts:
        return pydl_node

    return assign_stmts + [pydl_node]


@parse_ast.register(ast.AsyncWith)
def parse_asyncwith(node, module_data):
    context_expr = node.items[0].context_expr

    intf = find_name_expression(context_expr, module_data)
    scope, block_intf = intf_parse(intf=intf,
                                   target=node.items[0].optional_vars)

    module_data.hdl_locals.update(scope)

    pydl_node = blocks.IntfBlock(intf=block_intf, stmts=[])

    assign_stmts = find_subscript_expression(context_expr, module_data)
    parse_block(pydl_node, node.body, module_data)

    if not assign_stmts:
        return pydl_node

    return assign_stmts + [pydl_node]


@parse_ast.register(ast.If)
def parse_if(node, module_data):
    test_expr = find_data_expression(node.test, module_data)

    if isinstance(test_expr, expr.ResExpr):
        body_stmts = []
        if bool(test_expr.val):
            for stmt in node.body:
                pydl_stmt = parse_ast(stmt, module_data)
                add_to_list(body_stmts, pydl_stmt)
        elif hasattr(node, 'orelse'):
            for stmt in node.orelse:
                pydl_stmt = parse_ast(stmt, module_data)
                add_to_list(body_stmts, pydl_stmt)

        if body_stmts:
            return body_stmts

        return None
    else:
        pydl_node = blocks.IfBlock(_in_cond=test_expr, stmts=[])
        parse_block(pydl_node, node.body, module_data)
        if hasattr(node, 'orelse') and node.orelse:
            else_expr = expr.create_oposite(test_expr)
            pydl_node_else = blocks.IfBlock(_in_cond=else_expr, stmts=[])
            parse_block(pydl_node_else, node.orelse, module_data)
            top = blocks.ContainerBlock(stmts=[pydl_node, pydl_node_else])
            return top

        return pydl_node


@parse_ast.register(ast.Assert)
def parse_assert(node, module_data):
    test = parse_ast(node.test, module_data)
    msg = node.msg.s if node.msg else 'Assertion failed.'
    return expr.AssertExpr(test=test, msg=msg)


@parse_ast.register(ast.Num)
def parse_num(node, module_data):
    if node.n < 0:
        dtype = type(Int(node.n))
    else:
        dtype = type(Uint(node.n))

    return expr.ResExpr(dtype(node.n))


@parse_ast.register(ast.Name)
def parse_name(node, module_data):
    return get_context_var(node.id, module_data)


@parse_ast.register(ast.Attribute)
def parse_attribute(node, module_data):
    val = parse_ast(node.value, module_data)

    if isinstance(val, expr.AttrExpr):
        return expr.AttrExpr(val.val, val.attr + [node.attr])

    return expr.AttrExpr(val, [node.attr])


@parse_ast.register(ast.BinOp)
def parse_binop(node, module_data):
    return get_bin_expr(node.op, (node.left, node.right), module_data)


@parse_ast.register(ast.Compare)
def parse_compare(node, module_data):
    return get_bin_expr(node.ops[0], (node.left, node.comparators[0]),
                        module_data)


@parse_ast.register(ast.BoolOp)
def parse_boolop(node, module_data):
    return get_bin_expr(node.op, node.values, module_data)


@parse_ast.register(ast.UnaryOp)
def parse_unaryop(node, module_data):
    operand = find_data_expression(node.operand, module_data)
    if operand is None:
        return None

    if isinstance(operand, expr.ResExpr):
        return find_data_expression(node, module_data)

    operator = expr.OPMAP[type(node.op)]

    if operator == '!':
        return expr.create_oposite(operand)

    return expr.UnaryOpExpr(operand, operator)


@parse_ast.register(ast.Subscript)
def parse_subscript(node, module_data):
    val_expr = parse_ast(node.value, module_data)

    def get_slice(_slice, val_expr):
        if hasattr(_slice, 'value'):
            data_index = typeof(val_expr.dtype, (Array, Integer))
            if not data_index:
                try:
                    data_index = isinstance(
                        val_expr,
                        expr.OperandVal) and (len(val_expr.op.intf) > 1)
                except (TypeError, AttributeError):
                    pass

            if data_index:
                index = find_data_expression(_slice.value, module_data)
                if isinstance(index, expr.ResExpr):
                    index = int(index.val)

                return index
            else:
                return eval_local_expression(_slice.value,
                                             module_data.local_namespace)
        else:

            def slice_eval():
                for field in ['lower', 'upper', 'step']:
                    if not getattr(_slice, field):
                        yield None
                    else:
                        yield eval_local_expression(
                            getattr(_slice, field),
                            module_data.local_namespace)

            slice_args = list(slice_eval())

            index = slice(*slice_args)

            return index

    index = get_slice(node.slice, val_expr)

    if hasattr(node.value, 'id') and node.value.id in module_data.out_intfs:
        # conditional assginment, not subscript
        for i, port in zip(range(len(val_expr.op.intf)),
                           module_data.out_ports.values()):
            port.context = expr.BinOpExpr((index, expr.ResExpr(i)), '==')
        return None

    if not isinstance(index, slice) and isinstance(val_expr, expr.ConcatExpr):
        pydl_node = val_expr.operands[index]
    else:
        if isinstance(index, int) or isinstance(index, slice):
            index = val_expr.dtype.index_norm(index)[0]

        # TODO: Support array of indices
        pydl_node = expr.SubscriptExpr(val_expr, index)

    if pydl_node.dtype is Unit:
        return expr.ResExpr(Unit())

    return pydl_node


@parse_ast.register(ast.Tuple)
def parse_tuple(node, module_data):
    items = [find_data_expression(item, module_data) for item in node.elts]
    return expr.ConcatExpr(items)


@parse_ast.register(ast.Break)
def parse_break(node, module_data):
    return expr.BreakExpr()
