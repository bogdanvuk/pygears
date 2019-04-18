import ast

from pygears.typing import Queue, Tuple, typeof
from .ast_data_utils import find_data_expression

from . import hdl_types as ht


def get_bin_expr(op, operand1, operand2, module_data):
    op1 = find_data_expression(operand1, module_data)
    op2 = find_data_expression(operand2, module_data)

    if isinstance(op, ast.MatMult):
        return ht.ConcatExpr((op2, op1))

    operator = ht.OPMAP[type(op)]
    return ht.BinOpExpr((op1, op2), operator)


def intf_parse(intf, target):
    scope = gather_control_stmt_vars(target, intf)
    block_intf = ht.IntfDef(intf=intf.intf, _name=intf.name, context='valid')
    return scope, block_intf


def gather_control_stmt_vars(variables, intf, attr=None, dtype=None):
    if dtype is None:
        dtype = intf.dtype
    if attr is None:
        attr = []
    else:
        for sub_attr in attr:
            dtype = dtype[sub_attr]

    scope = {}
    if isinstance(variables, ast.Tuple):
        for i, var in enumerate(variables.elts):
            if isinstance(var, ast.Name):
                scope[var.id] = ht.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(var, ast.Starred):
                scope[var.id] = ht.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(var, ast.Tuple):
                scope.update(
                    gather_control_stmt_vars(var, intf,
                                             attr + [dtype.fields[i]]))
    else:
        if isinstance(intf, ht.IntfDef):
            scope[variables.id] = intf
        else:
            scope[variables.id] = ht.AttrExpr(intf, attr)

    return scope


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)
    if isinstance(arg_nodes, list):
        assert len(arg_nodes) == out_num
        input_vars = arg_nodes
    elif isinstance(arg_nodes, ht.OperandVal) and out_num > 1:
        intf = arg_nodes.op
        assert len(intf.intf) == out_num
        input_vars = []
        for i in range(len(intf.intf)):
            input_vars.append(ht.SubscriptExpr(val=intf, index=ht.ResExpr(i)))
    else:
        assert out_num == 1
        input_vars = [arg_nodes]

    args = []
    for arg, intf in zip(input_vars, out_ports.values()):
        port_t = intf.dtype
        if typeof(port_t, Queue) or typeof(port_t, Tuple):
            if isinstance(arg, ht.ConcatExpr):
                for i in range(len(arg.operands)):
                    if isinstance(arg.operands[i], ht.CastExpr) and (
                            arg.operands[i].cast_to == port_t[i]):
                        pass
                    else:
                        arg.operands[i] = ht.CastExpr(
                            operand=arg.operands[i], cast_to=port_t[i])

            args.append(arg)
        else:
            args.append(ht.CastExpr(operand=arg, cast_to=port_t))

    if len(args) == 1:
        return args[0]

    return args
