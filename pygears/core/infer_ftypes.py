from .type_match import type_match, TypeMatchError
from pygears.typing.base import param_subs, is_template
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


def infer_ftypes(ftypes, args, namespace={}, params={}):

    # Add all registered objects (types and transformations) to the namespace
    namespace = dict(namespace)
    namespace.update(registry('TypeArithNamespace'))

    # Copy structures that will be changed
    ftypes = list(ftypes)
    match = dict(params)

    substituted = True
    unresolved = False
    # Allow for keyword argument values to be templates and provide
    # a mechanism to resolve these template arguments
    while substituted:
        substituted = False
        # Loops until none of the parameters has been additionally resolved
        for p, v in match.items():
            if is_template(v):
                unresolved = True
                new_p = param_subs(v, match, {})
                if (not isinstance(new_p, str)) or new_p != match[p]:
                    match[p] = new_p
                    substituted = True
                    break

        if substituted:
            continue

        for i in range(len(ftypes)):
            if is_template(ftypes[i]) or (not type_is_specified(ftypes[i])):
                unresolved = True
                if i < len(args):
                    # Match input template to received arguments
                    try:
                        match.update(
                            type_match(
                                args[i],
                                ftypes[i],
                                match,
                                allow_incomplete=True))
                    except TypeMatchError as e:
                        raise TypeMatchError(
                            f'{str(e)}\n - when deducing type for argument '
                            f'{ftypes.index(ftypes[i])}')

                ft = param_subs(ftypes[i], match, namespace)
                if repr(ft) != repr(ftypes[i]):
                    ftypes[i] = ft
                    substituted = True
                    break

    return ftypes, match
