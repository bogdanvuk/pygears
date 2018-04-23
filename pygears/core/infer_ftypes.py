from .type_match import type_match, TypeMatchError
from pygears.typing.base import param_subs, is_template, GenericMeta
from pygears.registry import registry
import types


def type_is_specified(t):
    try:
        return t.is_specified()
    except Exception as e:
        if t is None:
            return True
        else:
            return False


def resolve_param(param, match, namespace):

    if isinstance(param, GenericMeta) and not param.is_specified():
        new_p = param_subs(param, match, namespace)
        if repr(new_p) != repr(param):
            return True, new_p

    elif isinstance(param, bytes):
        return True, eval(param, namespace, match)

    return False, None


def infer_ftypes(ftypes, args, namespace={}, params={},
                 allow_incomplete=False):

    # Add all registered objects (types and transformations) to the namespace
    namespace = dict(namespace)
    namespace.update(registry('TypeArithNamespace'))

    # Copy structures that will be changed
    ftypes = list(ftypes)
    postponed = {
        name: val
        for name, val in params.items() if isinstance(val, bytes)
    }
    match = {
        name: val
        for name, val in params.items() if name not in postponed
    }

    substituted = True
    final_check = False
    # Allow for keyword argument values to be templates and provide
    # a mechanism to resolve these template arguments
    while substituted or final_check:
        substituted = False
        # Loops until none of the parameters has been additionally resolved
        for p, param in postponed.copy().items():
            if isinstance(param, bytes):
                try:
                    substituted, new_p = resolve_param(param, match, namespace)

                    if substituted:
                        # print(p, ': ', param, ' -> ', new_p)
                        match[p] = new_p
                        del postponed[p]
                        break
                except Exception as e:
                    if final_check:
                        raise TypeMatchError(f'{str(e)} - when resolving '
                                             f'parameter {p}: {param}')

        if substituted:
            continue

        for i in range(len(ftypes)):
            if isinstance(ftypes[i],
                          (str, bytes)) or (not type_is_specified(ftypes[i])):
                # if is_template(ftypes[i]) or (not type_is_specified(ftypes[i])):
                if i < len(args):
                    # Match input template to received arguments
                    try:
                        match.update(
                            type_match(
                                args[i],
                                ftypes[i],
                                match,
                                allow_incomplete=(not final_check)))
                    except Exception as e:
                        raise TypeMatchError(
                            f'{str(e)}\n - when deducing type for argument '
                            f'{ftypes.index(ftypes[i])}')

            try:
                substituted, ft = resolve_param(ftypes[i], match, namespace)

                if substituted and ft.is_specified():
                    # print(i, ': ', ftypes[i], ' -> ', ft)
                    ftypes[i] = ft
                    break
            except Exception as e:
                if final_check:
                    raise TypeMatchError(f'{str(e)} - when resolving '
                                         f'argument type {i}: {ftypes[i]}')
                # ft = param_subs(ftypes[i], match, namespace)
                # if repr(ft) != repr(ftypes[i]):
                #     ftypes[i] = ft
                #     substituted = True
                #     break

        final_check = not substituted and not final_check

        # if not final_check and not substituted:
        #     print(match)

    for name, value in match.items():
        if isinstance(value, bytes) or (isinstance(value, GenericMeta)
                                        and not value.is_specified()):
            raise TypeMatchError(f'Parameter {name} unresolved: {value}')

    return ftypes, match
