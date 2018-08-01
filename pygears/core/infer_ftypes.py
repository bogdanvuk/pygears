import collections
import copy

from pygears.registry import registry
from pygears.typing.base import GenericMeta, param_subs, TypingMeta

from .type_match import TypeMatchError, type_match


def is_type_iterable(t):
    return (not isinstance(t, (str, bytes))) and isinstance(
        t, collections.Iterable)


def _copy_field_names(t, pat):
    if isinstance(t, GenericMeta) and isinstance(
            pat, GenericMeta) and (issubclass(t.base, pat.base)):
        for ta, pa in zip(t.args, pat.args):
            _copy_field_names(ta, pa)

        if hasattr(pat, '__parameters__'):
            t.__parameters__ = pat.__parameters__


def copy_field_names(t, pat):
    t = copy.copy(t)
    _copy_field_names(t, pat)
    return t


def type_is_specified(t):
    try:
        return t.is_specified()
    except Exception as e:
        if t is None:
            return True
        elif is_type_iterable(t):
            return all(type_is_specified(subt) for subt in t)
        else:
            return False


def resolve_param(val, match, namespace):

    is_templated_type = (isinstance(val, GenericMeta)
                         and (not val.is_generic()))

    if ((is_templated_type or is_type_iterable(val))
            and (not type_is_specified(val))):
        new_p = param_subs(val, match, namespace)
        if repr(new_p) != repr(val):
            return True, new_p

    elif isinstance(val, bytes):
        return True, eval(val, namespace, match)

    return False, None


def infer_ftypes(params, args, namespace={}, allow_incomplete=False):

    # Add all registered objects (types and transformations) to the namespace
    namespace = dict(namespace)
    namespace.update(registry('TypeArithNamespace'))

    def is_postponed(name, val):
        if isinstance(val, bytes):
            return True
        if (name in args):
            return True

        if (name == 'return'):
            return not type_is_specified(val)

        return False

    postponed = {
        name: val
        for name, val in params.items() if is_postponed(name, val)
    }
    match = {
        name: val
        for name, val in params.items() if name not in postponed
    }

    # print('Postponed: ', postponed)
    # print('Match: ', match)

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

                    match.update(
                        type_match(
                            args[name],
                            templ,
                            match,
                            allow_incomplete=(not final_check)))
                except Exception as e:
                    raise TypeMatchError(
                        f"{str(e)}\n - when deducing type for argument "
                        f"'{name}'")
            try:
                substituted, new_p = resolve_param(val, match, namespace)
                if name in args:
                    new_p = args[name]
                    substituted = type_is_specified(new_p)

                if substituted:
                    if name in args:
                        new_p = copy_field_names(new_p, params[name])

                    match[name] = new_p
                    del postponed[name]
                    break
            except Exception as e:
                if final_check:
                    raise type(e)(f'{str(e)} - when resolving '
                                  f'parameter {name}: {val}')

        final_check = not substituted and not final_check

    # print('Final postponed: ', postponed)
    # print('Final match: ', match)

    for name, val in args.items():
        type_match(val, match[name], {})

    if postponed:
        name, value = next(iter(postponed.items()))
        print(match)
        raise TypeMatchError(f'Parameter "{name}" unresolved: {value}')

    return match
