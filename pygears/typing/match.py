from pygears.conf import reg
from pygears.typing.base import Any, GenericMeta, type_repr, typeof, T


class TypeMatchError(Exception):
    pass


def _get_match_conds_rec(t, pat, matches):
    # Ignore type template arguments, i.e.: 'T2' in Tuple[1, 2, 3, 'T2']
    if isinstance(t, str):
        return t

    if (t == Any) or (pat == Any):
        return t

    if t == pat:
        return t

    if isinstance(pat, T):
        t = _get_match_conds_rec(t, pat.__bound__, matches)
        pat = pat.__name__

    # Did we reach the parameter name?
    if isinstance(pat, str):
        if pat in matches:
            # If the parameter name is already bound, check if two deductions
            # are same
            # if repr(t) != repr(matches[pat]) and t != Any and matches[pat] != Any:
            if t != matches[pat] and t != Any and matches[pat] != Any:
                raise TypeMatchError(
                    f'Ambiguous match for parameter "{pat}": {type_repr(t)} '
                    f"and {type_repr(matches[pat])}")
        else:
            try:
                # TODO: Should probably use globals of the string. See: Python
                # 3.10. typing.get_type_hints()
                res = eval(pat, reg['gear/type_arith'], matches)
                if t != res:
                    raise TypeMatchError(
                        f"{type_repr(t)} cannot be matched to {type_repr(res)}")
            except Exception as e:
                matches[pat] = t

        return t

    if not (isinstance(t, GenericMeta) and isinstance(pat, GenericMeta)
            and typeof(t.base, pat.base)):
        raise TypeMatchError(
            "{} cannot be matched to {}".format(type_repr(t), type_repr(pat)))

    # TODO: There might be multiple levels of inheritance when the types are
    # created, maybe they are compatible base on some of their more distant
    # base classes
    if pat.args:
        if len(t.args) != len(pat.args):
            raise TypeMatchError(
                "{} cannot be matched to {}".format(type_repr(t), type_repr(pat)))

        args = []
        for ta, pa in zip(t.args, pat.args):
            try:
                res = _get_match_conds_rec(ta, pa, matches)
                args.append(res)
            except TypeMatchError as e:
                raise TypeMatchError(
                    f'{str(e)}\n - when matching {repr(t)} to {repr(pat)}')

        # if hasattr(pat, '__parameters__'):
        args = {name: a for name, a in zip(pat.fields, args)}
    else:
        args = t.args

    # TODO: Revisit this Don't create a new type class when class has no
    # specified templates, so that we don't end up with multiple different
    # base class objects, that cannot be correctly tested with "issubclass"
    if not args and not t.args:
        return t
    else:
        return t.__class__(t.__name__, t.__bases__, dict(t.__dict__), args=args)


def get_match_conds(t, pat, matches=None):
    if matches is None:
        matches = {}
    else:
        matches = dict(matches)

    res = _get_match_conds_rec(t, pat, matches)
    return matches, res


def match(t, pat, matches=None):
    try:
        upd_matches, res = get_match_conds(t, pat, matches)
    except TypeMatchError:
        return None

    if matches is not None:
        matches.clear()
        matches.update(upd_matches)

    return res
