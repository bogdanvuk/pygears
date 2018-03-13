from .type_match import type_match, TypeMatchError
from pygears.typing.base import param_subs
from pygears.registry import registry


def infer_ftypes(ftypes, args, namespace={}, params={}):

    # Add all registered objects (types and transformations) to the namespace
    namespace = dict(namespace)
    namespace.update(registry('TypeArithNamespace'))

    ftypes = list(ftypes)
    args = list(args)

    match = dict(params)
    for pat, ta in zip(ftypes, args):
        try:
            match.update(type_match(ta, pat, match))
        except TypeMatchError as e:
            raise TypeMatchError(
                f'{str(e)}\n - when deducing type for argument '
                f'{ftypes.index(pat)}')

    for i in range(len(args)):
        ftypes[i] = param_subs(ftypes[i], match, namespace)

    return ftypes, match
