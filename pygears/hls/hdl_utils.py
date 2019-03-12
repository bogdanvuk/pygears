import ast
import logging

from pygears import PluginBase
from pygears.conf import register_custom_log, registry
from pygears.typing import Int, Uint, is_type

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


def hls_log():
    return logging.getLogger('svgen')


class HLSPlugin(PluginBase):
    @classmethod
    def bind(cls):
        register_custom_log('svgen', logging.WARNING)
