import ast

from .ast_parse import parse_node, parse_ast
from .hls_expressions import (ConcatExpr, Expr, IntfDef, IntfStmt, RegDef,
                              AttrExpr, RegNextStmt, ResExpr, VariableDef,
                              VariableStmt)
from .pydl_types import IntfBlock
from .utils import (VisitError, add_to_list, find_assign_target,
                    find_data_expression, interface_operations,
                    eval_expression)


@parse_node(ast.AugAssign)
def parse_augassign(node, module_data):
    target_load = ast.Name(node.target.id, ast.Load())
    val = ast.BinOp(target_load, node.op, node.value)
    assign_node = ast.Assign([node.target], val)
    return parse_assign(assign_node, module_data)


@parse_node(ast.Assign)
def parse_assign(node, module_data):
    names = find_assign_target(node)
    indexes = [None] * len(names)

    for i, name_node in enumerate(node.targets):
        if hasattr(name_node, 'value'):
            indexes[i] = parse_ast(name_node, module_data)

    vals, block = find_assign_value(node, module_data, names)
    if vals is None:
        return block

    res = []
    assert len(names) == len(indexes) == len(vals), 'Assign lenght mismatch'
    for name, index, val in zip(names, indexes, vals):
        from pygears.core.gear import OutSig
        if (name in module_data.variables) and (isinstance(
                val, ResExpr)) and (isinstance(val.val, OutSig)):
            return None

        res.append(assign(name, module_data, index, val))

    assert len(names) == len(res), 'Assign target and result lenght mismatch'

    if block:
        add_to_list(block.stmts, res)
        return block

    if len(names) == 1:
        return res[0]

    return res


def find_assign_value(node, module_data, names):
    intf_assigns = [n in module_data.in_intfs for n in names]
    assert intf_assigns[
        1:] == intf_assigns[:
                            -1], f'Mixed assignment of interfaces and variables not allowed'

    if isinstance(node.value, ast.Await):
        vals, block = find_await_value(node.value, module_data)
    else:
        try:
            vals = find_data_expression(node.value, module_data)
            block = None
        except Exception as e:
            vals = eval_expression(node.value, module_data.local_namespace)
            for n in names:
                del module_data.variables[n]
                module_data.pyvars[n] = vals
                module_data.local_namespace[n] = vals
                return None, None

    if len(names) == 1:
        return [vals], block

    if isinstance(vals, ConcatExpr):
        return vals.operands, block

    if isinstance(vals, ResExpr):
        return [ResExpr(v) for v in vals.val], block

    if isinstance(vals, IntfDef) and len(names) > 1:

        def find_field(names, intf, dtype, scope):
            if len(names) > len(dtype.fields):
                scope[names[-1]] = AttrExpr(intf, [dtype.fields[-1]])
                find_field(names[:-1], intf, dtype[0], scope)
            else:
                for i, name in enumerate(names):
                    scope[name] = AttrExpr(intf, [dtype.fields[i]])

        scope = {}
        find_field(names, vals, vals.dtype, scope)
        module_data.hdl_locals.update(scope)

        return None, None

    raise VisitError('Unknown assginment value')


def find_await_value(node, module_data):
    _, (intf_name, intf_method) = interface_operations(node.value)

    if intf_method == 'get':
        intf = module_data.hdl_locals.get(intf_name, None)
        assert isinstance(intf, IntfDef)
        intf_to_await = IntfDef(intf=intf.intf,
                                _name=intf.name,
                                context='valid')
    else:
        raise VisitError('Await only supports interface get method')

    await_node = IntfBlock(intf=intf_to_await, stmts=[])
    assign_value = parse_ast(node.value, module_data)

    return assign_value, await_node


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
            module_data.hdl_locals[name] = IntfDef(intf=tuple(
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
