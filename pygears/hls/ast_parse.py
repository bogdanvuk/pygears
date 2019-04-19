import ast
import itertools
from functools import singledispatch

from pygears.typing import Array, Int, Integer, Uint, Unit, typeof

from . import hdl_types as ht
from .utils import (add_to_list, cast_return, eval_local_expression,
                    find_assign_target, find_data_expression,
                    find_name_expression, get_bin_expr, get_context_var,
                    intf_parse)


@singledispatch
def parse_ast(node, module_data):
    """Used by default. Called if no explicit function exists for a node."""
    print(f'HERE: for {node}')
    for _, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    parse_ast(item, module_data)
        elif isinstance(value, ast.AST):
            parse_ast(value, module_data)


def parse_block(hdl_node, body, module_data):

    # self.enter_block(hdl_node)

    for stmt in body:
        res_stmt = parse_ast(stmt, module_data)
        if res_stmt is not None:
            # if self.await_found:
            #     await_node = ht.IntfBlock(
            #         intf=self.await_found, stmts=[res_stmt])
            #     self.await_found = None
            #     hdl_node.stmts.append(await_node)
            # else:
            #     hdl_node.stmts.append(res_stmt)
            add_to_list(hdl_node.stmts, res_stmt)

    # self.exit_block()

    return hdl_node


@parse_ast.register(ast.AsyncFunctionDef)
def parse_async_func(node, module_data):
    hdl_node = ht.Module(stmts=[])

    # initialization for register without explicit assign in code
    reg_names = list(module_data.regs.keys())
    assign_names = list(
        itertools.chain.from_iterable(
            find_assign_target(stmt) for stmt in node.body
            if isinstance(stmt, ast.Assign)))
    missing_reg = [name for name in reg_names if name not in assign_names]
    for name in missing_reg:
        module_data.hdl_locals[name] = ht.RegDef(module_data.regs[name], name)

    return parse_block(hdl_node, node.body, module_data)


@parse_ast.register(ast.Expr)
def parse_expr(node, module_data):
    if isinstance(node.value, ast.Yield):
        return parse_yield(node.value, module_data)

    return None


@parse_ast.register(ast.Yield)
def parse_yield(node, module_data):
    if isinstance(node.value, ast.Tuple) and len(module_data.out_ports) > 1:
        ports = []
        expr = [
            find_data_expression(item, module_data) for item in node.value.elts
        ]
        for i, val in enumerate(expr):
            if not (isinstance(val, ht.ResExpr) and val.val is None):
                ports.append(list(module_data.out_ports.values())[i])
    else:
        expr = parse_ast(node.value, module_data)
        ports = list(module_data.out_ports.values())
    stmts = []
    add_to_list(stmts, cast_return(expr, module_data.out_ports))
    return ht.Yield(stmts=stmts, ports=ports)


@parse_ast.register(ast.Call)
def parse_call_wrapper(node, module_data):
    from .ast_call import parse_call
    return parse_call(node, module_data)


@parse_ast.register(ast.For)
def parse_for_wrapper(node, module_data):
    from .ast_for import parse_for
    return parse_for(node, module_data)


@parse_ast.register(ast.While)
def parse_while(node, module_data):
    test = find_data_expression(node.test, module_data)
    multi = []
    if isinstance(test, ht.ResExpr) and test.val:
        multi = True
    hdl_node = ht.Loop(
        _in_cond=test,
        stmts=[],
        _exit_cond=ht.create_oposite(test),
        multicycle=multi)

    return parse_block(hdl_node, node.body, module_data)


@parse_ast.register(ast.Assign)
def parse_assign_wrapper(node, module_data):
    from .ast_assign import parse_assign
    return parse_assign(node, module_data)


@parse_ast.register(ast.AugAssign)
def parse_augassign(node, module_data):
    target_load = ast.Name(node.target.id, ast.Load())
    expr = ast.BinOp(target_load, node.op, node.value)
    assign_node = ast.Assign([node.target], expr)
    return parse_assign_wrapper(assign_node, module_data)


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

    hdl_node = ht.IntfLoop(intf=loop_intf, stmts=[], multicycle=scope)

    assign_stmts = find_subscript_expression(node.iter, module_data)
    parse_block(hdl_node, node.body, module_data)

    if not assign_stmts:
        return hdl_node

    return assign_stmts + [hdl_node]


@parse_ast.register(ast.AsyncWith)
def parse_asyncwith(node, module_data):
    context_expr = node.items[0].context_expr

    intf = find_name_expression(context_expr, module_data)
    scope, block_intf = intf_parse(
        intf=intf, target=node.items[0].optional_vars)

    module_data.hdl_locals.update(scope)

    hdl_node = ht.IntfBlock(intf=block_intf, stmts=[])

    assign_stmts = find_subscript_expression(context_expr, module_data)
    parse_block(hdl_node, node.body, module_data)

    if not assign_stmts:
        return hdl_node

    return assign_stmts + [hdl_node]


@parse_ast.register(ast.If)
def parse_if(node, module_data):
    expr = find_data_expression(node.test, module_data)

    if isinstance(expr, ht.ResExpr):
        body_stmts = []
        if bool(expr.val):
            for stmt in node.body:
                hdl_stmt = parse_ast(stmt, module_data)
                add_to_list(body_stmts, hdl_stmt)
        elif hasattr(node, 'orelse'):
            for stmt in node.orelse:
                hdl_stmt = parse_ast(stmt, module_data)
                add_to_list(body_stmts, hdl_stmt)

        if body_stmts:
            return body_stmts

        return None
    else:
        hdl_node = ht.IfBlock(_in_cond=expr, stmts=[])
        parse_block(hdl_node, node.body, module_data)
        if hasattr(node, 'orelse') and node.orelse:
            else_expr = ht.create_oposite(expr)
            hdl_node_else = ht.IfBlock(_in_cond=else_expr, stmts=[])
            parse_block(hdl_node_else, node.orelse, module_data)
            top = ht.ContainerBlock(stmts=[hdl_node, hdl_node_else])
            return top

        return hdl_node


@parse_ast.register(ast.Assert)
def parse_assert(node, module_data):
    test = parse_ast(node.test, module_data)
    msg = node.msg.s if node.msg else 'Assertion failed.'
    return ht.AssertExpr(test=test, msg=msg)


@parse_ast.register(ast.Num)
def parse_num(node, module_data):
    if node.n < 0:
        dtype = type(Int(node.n))
    else:
        dtype = type(Uint(node.n))

    return ht.ResExpr(dtype(node.n))


@parse_ast.register(ast.Name)
def parse_name(node, module_data):
    return get_context_var(node.id, module_data)


@parse_ast.register(ast.Attribute)
def parse_attribute(node, module_data):
    expr = parse_ast(node.value, module_data)

    if isinstance(expr, ht.AttrExpr):
        return ht.AttrExpr(expr.val, expr.attr + [node.attr])

    return ht.AttrExpr(expr, [node.attr])


@parse_ast.register(ast.BinOp)
def parse_binop(node, module_data):
    return get_bin_expr(node.op, node.left, node.right, module_data)


@parse_ast.register(ast.Compare)
def parse_compare(node, module_data):
    return get_bin_expr(node.ops[0], node.left, node.comparators[0],
                        module_data)


@parse_ast.register(ast.BoolOp)
def parse_boolop(node, module_data):
    return get_bin_expr(node.op, node.values[0], node.values[1], module_data)


@parse_ast.register(ast.UnaryOp)
def parse_unaryop(node, module_data):
    operand = find_data_expression(node.operand, module_data)
    if operand is None:
        return None

    if isinstance(operand, ht.ResExpr):
        return find_data_expression(node, module_data)

    operator = ht.OPMAP[type(node.op)]

    if operator == '!':
        return ht.create_oposite(operand)

    return ht.UnaryOpExpr(operand, operator)


@parse_ast.register(ast.Subscript)
def parse_subscript(node, module_data):
    val_expr = parse_ast(node.value, module_data)

    if hasattr(node.slice, 'value'):
        data_index = typeof(val_expr.dtype, (Array, Integer))
        if not data_index:
            try:
                data_index = isinstance(
                    val_expr, ht.OperandVal) and (len(val_expr.op.intf) > 1)
            except TypeError:
                pass

        if data_index:
            index = find_data_expression(node.slice.value, module_data)
            if isinstance(index, ht.ResExpr):
                index = int(index.val)
        else:
            index = eval_local_expression(node.slice.value,
                                          module_data.local_namespace)
    else:
        slice_args = [
            eval_local_expression(
                getattr(node.slice, field), module_data.local_namespace)
            for field in ['lower', 'upper'] if getattr(node.slice, field)
        ]

        index = slice(*tuple(arg for arg in slice_args))
        if index.start is None:
            index = slice(0, index.stop, index.step)

    if hasattr(node.value, 'id') and node.value.id in module_data.out_intfs:
        # conditional assginment, not subscript
        for i, port in zip(
                range(len(val_expr.op.intf)), module_data.out_ports.values()):
            port.context = ht.BinOpExpr((index, ht.ResExpr(i)), '==')
        return None

    hdl_node = ht.SubscriptExpr(val_expr, index)

    if hdl_node.dtype is Unit:
        return ht.ResExpr(Unit())

    return hdl_node


@parse_ast.register(ast.Tuple)
def parse_tuple(node, module_data):
    items = [find_data_expression(item, module_data) for item in node.elts]
    return ht.ConcatExpr(items)
