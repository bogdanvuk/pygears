import ast
import logging

from pygears import PluginBase
from pygears.conf import register_custom_log, registry
from pygears.typing import Int, Queue, Tuple, Uint, is_type, typeof

from . import hls_expressions as expr
from .pydl_types import Block, Yield

ASYNC_TYPES = (Yield, )
INTF_METHODS = ('get_nb', 'get', 'put', 'put_nb')


class VisitError(Exception):
    pass


class AstTypeError(Exception):
    pass


def set_pg_type(ret):
    if ret is None:
        return ret

    if not is_type(type(ret)):
        if isinstance(ret, (list, tuple)):
            return tuple([set_pg_type(r) for r in ret])

        if ret < 0:
            ret = Int(ret)
        else:
            ret = Uint(ret)

    return ret


def interface_operations(node):
    if isinstance(node, ast.Await):
        return True, None

    if isinstance(node, ast.Call):
        if hasattr(node.func, 'value'):
            if hasattr(node.func, 'attr'):
                if node.func.attr in INTF_METHODS:
                    return True, (node.func.value.id, node.func.attr)

    return False, None


def eval_expression(node, local_namespace):
    types = registry('gear/type_arith').copy()
    types.update(local_namespace)

    flag, _ = interface_operations(node)
    if flag:
        raise NameError

    return eval(
        compile(
            ast.Expression(ast.fix_missing_locations(node)),
            filename="<ast>",
            mode="eval"), types, globals())


def eval_local_expression(node, local_namespace):
    return eval(
        compile(ast.Expression(node), filename="<ast>", mode="eval"),
        local_namespace, globals())


def find_target(node):
    if hasattr(node, 'id'):
        return node.id

    if hasattr(node, 'value'):
        return node.value.id

    if isinstance(node, ast.Tuple):
        return [el.id for el in node.elts]

    raise VisitError('Unknown target type')


def find_assign_target(node):
    names = []

    for target in node.targets:
        add_to_list(names, find_target(target))

    return names


def find_for_target(node):
    if isinstance(node.target, ast.Tuple):
        return [x.id for x in node.target.elts]

    return [node.target.id]


def check_if_blocking(stmt):
    if isinstance(stmt, ASYNC_TYPES):
        return stmt
    if isinstance(stmt, Block):
        return find_hier_blocks(stmt.stmts)
    return None


def find_hier_blocks(body):
    hier = []
    for stmt in body:
        block = check_if_blocking(stmt)
        if block:
            hier.append(block)
    return hier


def add_to_list(orig_list, extention):
    if extention:
        orig_list.extend(
            extention if isinstance(extention, list) else [extention])


def get_state_cond(state_id):
    return expr.BinOpExpr(('state_reg', state_id), '==')


def state_expr(state_ids, prev_cond):
    state_cond = get_state_cond(state_ids[0])
    for state_id in state_ids[1:]:
        state_cond = expr.or_expr(state_cond, get_state_cond(state_id))

    if prev_cond is not None:
        return expr.and_expr(prev_cond, state_cond)

    return state_cond


def get_bin_expr(op, operand1, operand2, module_data):
    op1 = find_data_expression(operand1, module_data)
    op2 = find_data_expression(operand2, module_data)

    if isinstance(op, ast.MatMult):
        return expr.ConcatExpr((op2, op1))

    operator = expr.OPMAP[type(op)]
    return expr.BinOpExpr((op1, op2), operator)


def intf_parse(intf, target):
    scope = gather_control_stmt_vars(target, intf)
    if isinstance(intf, expr.IntfDef):
        block_intf = expr.IntfDef(
            intf=intf.intf, _name=intf.name, context='valid')
    else:
        block_intf = expr.IntfDef(intf=intf, _name=None, context='valid')
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
                scope[var.id] = expr.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(var, ast.Starred):
                scope[var.id] = expr.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(var, ast.Tuple):
                scope.update(
                    gather_control_stmt_vars(var, intf,
                                             attr + [dtype.fields[i]]))
    else:
        if attr:
            scope[variables.id] = expr.AttrExpr(intf, attr)
        else:
            scope[variables.id] = intf

    return scope


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)
    if isinstance(arg_nodes, list):
        assert len(arg_nodes) == out_num
        input_vars = arg_nodes
    elif isinstance(arg_nodes, expr.OperandVal) and out_num > 1:
        intf = arg_nodes.op
        assert len(intf.intf) == out_num
        input_vars = []
        for i in range(len(intf.intf)):
            input_vars.append(
                expr.SubscriptExpr(val=intf, index=expr.ResExpr(i)))
    else:
        assert out_num == 1
        input_vars = [arg_nodes]

    args = []
    for arg, intf in zip(input_vars, out_ports.values()):
        port_t = intf.dtype
        if typeof(port_t, Queue) or typeof(port_t, Tuple):
            if isinstance(arg, expr.ConcatExpr) and arg.dtype != port_t:
                for i in range(len(arg.operands)):
                    if isinstance(arg.operands[i], expr.CastExpr) and (
                            arg.operands[i].cast_to == port_t[i]):
                        pass
                    else:
                        arg.operands[i] = expr.CastExpr(
                            operand=arg.operands[i], cast_to=port_t[i])

            args.append(arg)
        else:
            args.append(expr.CastExpr(operand=arg, cast_to=port_t))

    if len(args) == 1:
        return args[0]

    return args


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

    if isinstance(var, expr.RegDef):
        return expr.OperandVal(var, 'reg')

    if isinstance(var, expr.VariableDef):
        return expr.OperandVal(var, 'v')

    if isinstance(var, expr.IntfDef):
        return expr.OperandVal(var, 's')

    return var


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if isinstance(ret, ast.AST):
        raise AstTypeError

    ret = set_pg_type(ret)

    return expr.ResExpr(ret)


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


def find_intf(name, module_data):
    if name in module_data.in_intfs:
        return module_data.in_intfs[name]

    if name in module_data.in_ports:
        return module_data.in_ports[name]

    raise VisitError('Unknown name expression')


def find_name_expression(node, module_data):
    if isinstance(node, ast.Call):
        arg_nodes = []
        for arg in node.args:
            add_to_list(arg_nodes, find_name_expression(arg, module_data))

        from .ast_call import call_func
        return call_func(node, arg_nodes, module_data)

    try:
        name = node.id
    except AttributeError:
        try:
            name = node.value.id
        except AttributeError:
            name = None

    if isinstance(node, ast.Starred):
        name = [p.basename for p in module_data.hdl_locals[name]]

    if name is not None:
        if not isinstance(name, list):
            return find_intf(name, module_data)

        return [find_intf(n, module_data) for n in name]

    raise VisitError('Unknown name expression')


def hls_log():
    return logging.getLogger('hls')


class HLSPlugin(PluginBase):
    @classmethod
    def bind(cls):
        register_custom_log('hls', logging.WARNING)
