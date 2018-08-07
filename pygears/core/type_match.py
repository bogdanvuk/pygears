import re

from pygears.registry import registry
from pygears.typing.base import Any, GenericMeta, type_repr


class TypeMatchError(Exception):
    pass


def _type_match_rec(t, pat, matches, allow_incomplete):

    # Ignore parameter names in type
    if isinstance(t, str):
        pass
    # Did we reach the parameter name?
    elif isinstance(pat, str):
        if pat in matches:
            # If the parameter name is already bound, check if two deductions
            # are same
            if repr(t) != repr(matches[pat]) and t != Any and matches[pat] != Any:
                raise TypeMatchError(
                    f"Ambiguous match for parameter {pat}: {type_repr(t)} "
                    f"and {type_repr(matches[pat])}")
        else:
            try:
                res = eval(pat, registry('TypeArithNamespace'), matches)
                if repr(t) != repr(res):
                    raise TypeMatchError(
                        f"{type_repr(t)} cannot be matched to {type_repr(res)}"
                    )
            except Exception as e:
                matches[pat] = t
                # if not allow_incomplete:
                # raise TypeMatchError(f"Cannot evaluate {type_repr(pat)}")
    elif (t == Any) or (pat == Any):
        pass
    elif isinstance(t, GenericMeta) and isinstance(
            pat, GenericMeta) and (issubclass(t.base, pat.base)):
        for ta, pa in zip(t.args, pat.args):
            try:
                _type_match_rec(
                    ta, pa, matches, allow_incomplete=allow_incomplete)
            except TypeMatchError as e:
                raise TypeMatchError(
                    f'{str(e)}\n - when matching {repr(t)} to {repr(pat)}')
    elif t == pat:
        pass
    else:
        raise TypeMatchError("{} cannot be matched to {}".format(
            type_repr(t), type_repr(pat)))


def type_match(t, pat, matches={}, allow_incomplete=False):
    matches = dict(matches)
    _type_match_rec(t, pat, matches, allow_incomplete=allow_incomplete)
    return matches
