from .ast_parse import parse_ast
from .hls_blocks import ContainerBlock
from .hls_expressions import (ConcatExpr, Expr, IntfDef, IntfStmt, RegDef,
                              RegNextStmt, ResExpr, VariableDef, VariableStmt)
from .utils import VisitError, find_assign_target, find_data_expression


def parse_assign(node, module_data):
    names = find_assign_target(node)
    indexes = [None] * len(names)

    for i, name_node in enumerate(node.targets):
        if hasattr(name_node, 'value'):
            indexes[i] = parse_ast(name_node, module_data)

    vals = find_assign_value(node, module_data, names)

    res = []
    assert len(names) == len(indexes) == len(vals), 'Assign lenght mismatch'
    for name, index, val in zip(names, indexes, vals):
        res.append(assign(name, module_data, index, val))

    assert len(names) == len(res), 'Assign target and result lenght mismatch'

    if len(names) == 1:
        return res[0]

    return ContainerBlock(stmts=res)


def find_assign_value(node, module_data, names):
    intf_assigns = [n in module_data.in_intfs for n in names]
    assert intf_assigns[
        1:] == intf_assigns[:
                            -1], f'Mixed assignment of interfaces and variables not allowed'

    vals = find_data_expression(node.value, module_data)

    if len(names) == 1:
        return [vals]

    if isinstance(vals, ConcatExpr):
        return vals.operands

    if isinstance(vals, ResExpr):
        return [ResExpr(v) for v in vals.val]

    raise VisitError('Unknown assginment value')


def assign(name, module_data, index, val):
    for var in module_data.variables:
        if var == name and not isinstance(module_data.variables[name], Expr):
            module_data.variables[name] = VariableDef(val, name)
            break

    if name in module_data.regs:
        return assign_reg(name, module_data, index, val)

    if name in module_data.variables:
        return assign_variable(name, module_data, index, val)

    if name in module_data.in_intfs:
        return assign_in_intf(name, module_data, index, val)

    if name in module_data.out_intfs:
        return assign_out_intf(name, module_data, index, val)

    raise VisitError('Unknown assginment type')


def assign_reg(name, module_data, index, val):
    if name not in module_data.hdl_locals:
        module_data.hdl_locals[name] = RegDef(val, name)
        return None

    if index:
        return RegNextStmt(index, val)

    return RegNextStmt(module_data.hdl_locals[name], val)


def assign_variable(name, module_data, index, val):
    if name not in module_data.hdl_locals:
        module_data.hdl_locals[name] = VariableDef(val, name)

    if index:
        return VariableStmt(index, val)

    return VariableStmt(module_data.hdl_locals[name], val)


def assign_in_intf(name, module_data, index, val):
    if name not in module_data.hdl_locals:
        module_data.hdl_locals[name] = IntfDef(intf=val.intf, _name=name)

    if index:
        return IntfStmt(index, val)

    if name in module_data.in_intfs:
        # when *din used as din[x], hdl_locals contain all interfaces
        # but a specific one is needed
        return IntfStmt(IntfDef(intf=val.intf, _name=name), val)

    return IntfStmt(module_data.hdl_locals[name], val)


def assign_out_intf(name, module_data, index, val):
    if name not in module_data.hdl_locals:
        if not all([v is None for v in val.val]):
            module_data.hdl_locals[name] = IntfDef(intf=val, _name=name)
        else:
            module_data.hdl_locals[name] = IntfDef(
                intf=tuple(
                    [intf.intf for intf in module_data.out_ports.values()]),
                _name=name)

    if index:
        return IntfStmt(index, val)

    ret_stmt = False
    if not hasattr(val, 'val'):
        ret_stmt = True
    elif isinstance(val.val, IntfDef):
        ret_stmt = True
    elif not all([v is None for v in val.val]):
        ret_stmt = True

    if ret_stmt:
        return IntfStmt(module_data.hdl_locals[name], val)

    return None
