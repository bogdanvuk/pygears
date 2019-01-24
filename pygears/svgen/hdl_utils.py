import hdl_types as ht

async_types = [ht.Yield]


def check_if_blocking(stmt):
    if type(stmt) in async_types:
        return stmt
    elif isinstance(stmt, ht.Block):
        return find_hier_blocks(stmt.stmts)
    else:
        return None


def find_hier_blocks(body):
    hier = []
    for stmt in body:
        b = check_if_blocking(stmt)
        if b:
            hier.append(b)
    return hier


def add_to_list(orig_list, extention):
    if extention:
        orig_list.extend(
            extention if isinstance(extention, list) else [extention])


def get_state_cond(id):
    return ht.BinOpExpr(('state_reg', id), '==')


def state_expr(state_ids, prev_cond):
    state_cond = get_state_cond(state_ids[0])
    for id in state_ids[1:]:
        state_cond = ht.or_expr(state_cond, get_state_cond(id))

    if prev_cond is not None:
        return ht.and_expr(prev_cond, state_cond)
    else:
        return state_cond
