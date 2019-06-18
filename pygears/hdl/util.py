COND_INLINE_THRESHOLD = 30


def inline_condition(cond, expr_func=None):
    if cond.target == 'rst_cond':
        return False

    if expr_func is not None:
        expr_val = expr_func(cond.val)
        cond.val = expr_val
    if len(str(cond.val)) > COND_INLINE_THRESHOLD:
        return False

    return True


def separate_conditions(stmts, config, expr_func=None):
    if 'conditions' in stmts:
        config['conditions'] = {
            x.target: x.val
            for x in stmts['conditions'].stmts
            if inline_condition(x, expr_func)
        }
        stmts['conditions'].stmts = [
            x for x in stmts['conditions'].stmts
            if x.target not in config['conditions']
        ]
