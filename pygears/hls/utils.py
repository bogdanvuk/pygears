import ast
import logging
from functools import reduce

from pygears import PluginBase
from pygears.conf import register_custom_log, registry
from pygears.typing import Int, Queue, Tuple, Uint, is_type, typeof

from . import hdl_types as ht

ASYNC_TYPES = (ht.Yield, )
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


def find_assign_target(node):
    names = []

    for target in node.targets:
        if hasattr(target, 'id'):
            names.append(target.id)
        elif hasattr(target, 'value'):
            names.append(target.value.id)
        elif isinstance(target, ast.Tuple):
            names.extend([el.id for el in target.elts])
        else:
            assert False, 'Unknown assignment type'

    return names


def find_for_target(node):
    if isinstance(node.target, ast.Tuple):
        return [x.id for x in node.target.elts]

    return [node.target.id]


def check_if_blocking(stmt):
    if isinstance(stmt, ASYNC_TYPES):
        return stmt
    if isinstance(stmt, ht.Block):
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
    return ht.BinOpExpr(('state_reg', state_id), '==')


def state_expr(state_ids, prev_cond):
    state_cond = get_state_cond(state_ids[0])
    for state_id in state_ids[1:]:
        state_cond = ht.or_expr(state_cond, get_state_cond(state_id))

    if prev_cond is not None:
        return ht.and_expr(prev_cond, state_cond)

    return state_cond


def break_comb_loop(visitor, loop_to_break, reg_name, var_name):
    loop_to_break_idx = visitor.scope.index(loop_to_break)

    # current loop iteration
    break_num = len(loop_to_break.
                    break_cond) if loop_to_break.break_cond is not None else 0

    # all sub conditions that lead to break
    if_block = next(block for block in visitor.scope[loop_to_break_idx:]
                    if isinstance(block, ht.IfBlock))
    block_idx = visitor.scope.index(if_block)

    sub_conds = [
        getattr(block, 'in_cond', None) for block in visitor.scope[block_idx:]
    ]

    # added reg. condition in case inputs change
    loop_cond_stmt = ast.parse(
        f'not {reg_name} or {reg_name}[{break_num}]').body[0]
    loop_reg_cond = visitor.visit(loop_cond_stmt.value)
    sub_conds.append(loop_reg_cond)

    # merged in condition for current iteration
    in_cond = ht.create_oposite(reduce(ht.and_expr, sub_conds, None))

    if loop_to_break.break_cond:
        break_conds = reduce(ht.and_expr,
                             loop_to_break.break_cond + [loop_reg_cond], None)
    else:
        break_conds = loop_reg_cond
        loop_to_break.break_cond = []

    if_block._in_cond = ht.and_expr(if_block._in_cond, break_conds)

    loop_to_break.break_cond.append(in_cond)

    # register current loop iteration
    loop_stmt = visitor.visit(
        ast.parse(f'{var_name}[{break_num}] = 1').body[0])
    visitor.scope[block_idx].stmts.insert(0, loop_stmt)


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
        return module_data.in_intfs[node.value.id]

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


def hls_log():
    return logging.getLogger('svgen')


class HLSPlugin(PluginBase):
    @classmethod
    def bind(cls):
        register_custom_log('svgen', logging.WARNING)
