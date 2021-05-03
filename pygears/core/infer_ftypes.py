import collections

from pygears.conf import reg
from pygears.typing.base import GenericMeta, param_subs, is_type, T

from pygears.typing import TypeMatchError, get_match_conds


def is_type_iterable(t):
    return (not isinstance(t, (str, bytes))) and isinstance(t, collections.abc.Iterable)


def _copy_field_names(t, pat):
    if isinstance(t, GenericMeta) and isinstance(pat, GenericMeta) and (issubclass(
            t.base, pat.base)):
        for ta, pa in zip(t.args, pat.args):
            _copy_field_names(ta, pa)

        if hasattr(pat, '__parameters__'):
            t.__parameters__ = pat.__parameters__


def copy_field_names(t, pat):
    t = t.copy()
    _copy_field_names(t, pat)
    return t


def type_is_specified(t):
    if isinstance(t, T):
        return False

    if is_type(t):
        return t.specified

    if t is None:
        return True
    elif isinstance(t, dict):
        return all(type_is_specified(subt) for subt in t.values())
    elif is_type_iterable(t):
        return all(type_is_specified(subt) for subt in t)
    elif isinstance(t, bytes):
        return False
    else:
        return True


def resolve_param(val, match, namespace):
    if isinstance(val, T):
        new_p = param_subs(val, match, namespace)
        if new_p != val:
            return True, new_p
        else:
            return False, None

    is_templated_type = (isinstance(val, GenericMeta) and (not val.is_generic()))

    if ((is_templated_type or is_type_iterable(val)) and (not type_is_specified(val))):
        new_p = param_subs(val, match, namespace)

        if repr(new_p) != repr(val):
            return True, new_p

    elif isinstance(val, bytes):
        return True, eval(val, namespace, match)

    return False, None


def infer_ftypes(params, args, namespace={}):
    # Add all registered objects (types and transformations) to the namespace
    namespace = dict(namespace)
    namespace.update(reg['gear/type_arith'])

    def is_postponed(name, val):
        if isinstance(val, bytes):
            return True
        if (name in args):
            return True

        if (name == 'return'):
            return not type_is_specified(val)

        return False

    postponed = {name: val for name, val in params.items() if is_postponed(name, val)}
    match = {name: val for name, val in params.items() if name not in postponed}

    substituted = True
    final_check = False
    # Allow for keyword argument values to be templates and provide
    # a mechanism to resolve these template arguments
    while substituted or final_check:
        substituted = False
        # Loops until none of the parameters has been additionally resolved
        for name, val in postponed.copy().items():

            if name in args:
                try:
                    templ = val
                    if isinstance(val, bytes):
                        templ = templ.decode()

                    match_update, res = get_match_conds(args[name], templ, match)
                    match.update(match_update)
                    args[name] = res

                    if type_is_specified(res):
                        if is_type(res):
                            res = copy_field_names(res, params[name])

                        args[name] = res
                        match[name] = res
                        del postponed[name]
                        substituted = True
                        break
                    else:
                        postponed[name] = res

                except TypeMatchError as e:
                    err = TypeMatchError(
                        f'{str(e)}\n - when deducing type for argument '
                        f'"{name}"')
                    err.params = match
                    raise err
            else:
                try:
                    substituted, new_p = resolve_param(val, match, namespace)
                    if substituted and (name == 'return'):
                        substituted = type_is_specified(new_p)

                    if substituted:
                        if name == 'return':
                            substituted = type_is_specified(new_p)

                        match[name] = new_p
                        del postponed[name]
                        break
                    elif final_check:
                        if new_p is not None:
                            raise TypeMatchError(f'Incomplete type: {repr(new_p)}')
                        else:
                            raise TypeMatchError(f'Incomplete type: {repr(val)}')

                except Exception as e:
                    if final_check:
                        try:
                            arg_repr = str(e.args[0])
                        except:
                            arg_repr = repr(e.args[0])

                        if isinstance(val, bytes):
                            val_repr = val.decode()
                        else:
                            try:
                                val_repr = str(val)
                            except:
                                val_repr = repr(val)

                        if name == 'return':
                            err = type(e)(
                                f'{arg_repr}\n - when resolving '
                                f'return type "{val_repr}"')
                        else:
                            err = type(e)(
                                f'{arg_repr}\n - when resolving '
                                f'parameter "{name}": "{val_repr}"')
                        err.params = match
                        raise err

        final_check = not substituted and not final_check

    # print('Final postponed: ', postponed)
    # print('Final match: ', match)

    for name, val in args.items():
        get_match_conds(val, match[name], {})

    if postponed:
        name, value = next(iter(postponed.items()))
        err = TypeMatchError(f'Parameter "{name}" unresolved: {value}')
        err.params = match
        raise err

    return match
