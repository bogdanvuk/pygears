import ast

from . import hdl_types as ht
from .hdl_utils import AstTypeError, eval_expression, set_pg_type, VisitError


def find_intf_by_name(data, name):
    val = None

    for port in data.in_ports:
        if name == port:
            val = data.in_ports[port]
            break
    if val is None:
        for port in data.in_intfs:
            if name == port:
                val = data.in_intfs[port]
                break

    return val


def get_context_var(pyname, module_data):
    var = module_data.hdl_locals.get(pyname, None)

    if isinstance(var, ht.RegDef):
        return ht.OperandVal(var, 'reg')

    if isinstance(var, ht.VariableDef):
        return ht.OperandVal(var, 'v')

    if isinstance(var, ht.IntfDef):
        return ht.OperandVal(var, 's')

    return var


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if isinstance(ret, ast.AST):
        raise AstTypeError

    ret = set_pg_type(ret)

    return ht.ResExpr(ret)


def find_data_expression(node, module_data):
    if not isinstance(node, ast.AST):
        return node

    # when interfaces are assigned eval_data_expr is not allowed
    # because eval will execute the assignment and create extra gears
    # and connections for them
    name = None
    if hasattr(node, 'value') and hasattr(node.value, 'id'):
        name = node.value.id
    elif hasattr(node, 'id'):
        name = node.id

    if name is not None:
        val = find_intf_by_name(module_data, name)
        if val is not None:
            return val

    try:
        return eval_data_expr(node, module_data.local_namespace)
    except (NameError, AstTypeError, TypeError, AttributeError):
        from .ast_parse import parse_ast
        return parse_ast(node, module_data)


def find_name_expression(node, module_data):
    if isinstance(node, ast.Subscript):
        # input interface as array ie din[x]
        name = node.value.id
        val_expr = get_context_var(name, module_data)
        for i in range(len(val_expr)):
            py_stmt = f'if {node.slice.value.id} == {i}: {name} = {name}{i}'
            snip = ast.parse(py_stmt).body[0]
            raise VisitError('Must propagate scope')
            # stmt = self.visit(snip)
            # self.scope[-1].stmts.append(stmt)

        assert name in module_data.in_intfs
        return module_data.in_intfs[name]

    if node.id in module_data.in_intfs:
        return module_data.in_intfs[node.id]

    ret = eval_expression(node, module_data.local_namespace)

    local_names = list(module_data.local_namespace.keys())
    local_objs = list(module_data.local_namespace.values())

    name_idx = None
    for i, obj in enumerate(local_objs):
        if ret is obj:
            name_idx = i
            break

    name = local_names[name_idx]

    return module_data.hdl_locals.get(name, None)
