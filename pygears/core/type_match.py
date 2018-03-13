import re

from pygears.registry import registry
from pygears.typing.base import Any, GenericMeta, type_repr


class TypeMatchError(Exception):
    pass


class FormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _type_match_rec(t, pat, matches):

    # Ignore parameter names in type
    if isinstance(t, str):
        pass
    # Did we reach the parameter name?
    elif isinstance(pat, str):
        res = re.findall(r"\{(.*?)\}", pat)
        if res and ((len(res) > 1) or ('{' + res[0] + '}' != pat)):

            # formatter = string.Formatter()
            try:
                param_str = pat.format(**matches)
            except KeyError as e:
                raise TypeMatchError(
                    f'Missing value for argument(s) {e.args}, in '
                    f'substitution of template parameter "{pat}".')

            if repr(t) != repr(
                    eval(param_str, registry('TypeArithNamespace'))):
                raise TypeMatchError(
                    f'Template "{pat}" is an expresion. Matching to an'
                    f' expression is not currently supported.')
        elif len(res) == 0:
            raise TypeMatchError(
                f'Malformed template expresion "{pat}". Did you forget '
                'enclosing template arguments in curly braces?')
        else:
            # If the parameter name is already bound, but not to another
            # parameter name, check if two deductions are same if (pat in
            # matches) and (not isinstance(matches[pat], str)):
            if res[0] in matches:
                if repr(t) != repr(matches[res[0]]):
                    raise TypeMatchError(
                        "Ambiguous match for parameter {}: {} and {}".format(
                            res[0], type_repr(t), type_repr(matches[res[0]])))
            else:
                matches[res[0]] = t
    elif (t == Any) or (pat == Any):
        pass
    elif isinstance(t, GenericMeta) and isinstance(
            t, GenericMeta) and (t.base == pat.base):
        for ta, pa in zip(t.args, pat.args):
            try:
                _type_match_rec(ta, pa, matches)
            except TypeMatchError as e:
                raise TypeMatchError(
                    f'{str(e)}\n - when matching {repr(t)} to {repr(pat)}')
    elif t == pat:
        pass
    else:
        raise TypeMatchError("{} cannot be matched to {}".format(
            type_repr(t), type_repr(pat)))


def type_match(t, pat, matches={}):
    matches = dict(matches)
    _type_match_rec(t, pat, matches)
    return matches
