import copy
import functools
import inspect

from pygears.conf import Inject, inject, registry, PluginBase, safe_bind
from pygears.typing import Tuple, typeof

from .funcutils import FunctionMaker
from .partial import Partial
from .util import doublewrap, get_function_context_dict


def add_alternative(base, alter):
    alternatives = getattr(base, 'alternatives', [])
    alternatives.append(alter)
    gear_func = getattr(alter, '__wrapped__', alter)
    gear_func_to = getattr(base, '__wrapped__', base)

    gear_func.alternative_to = gear_func_to
    gear_func_to.alternatives = alternatives

    base.alternatives = alternatives


def alternative(*base_gear_defs):
    def gear_decorator(gear_def):
        for d in base_gear_defs:
            add_alternative(d.func, gear_def.func)
        return gear_def

    return gear_decorator


@inject
def find_invocation(func, extra_params=Inject('gear/params/extra')):
    invocation = []
    sig = inspect.signature(func)

    for name, param in sig.parameters.items():
        if param.kind == param.KEYWORD_ONLY:
            invocation.append(f'{name}={name}')
        elif param.kind == param.VAR_POSITIONAL:
            invocation.append(f'*{name}')
        elif param.kind != param.VAR_KEYWORD:
            invocation.append(name)

    if extra_params:
        for k, v in extra_params.items():
            invocation.append(f'{k}={k}')

    for name, param in sig.parameters.items():
        if param.kind == param.VAR_KEYWORD:
            invocation.append(f'**{name}')

    return ','.join(invocation)


def create_unpacked_tuple_alternative(g):

    args, *paramspec, annotations = inspect.getfullargspec(g.func)

    if len(args) != 1:
        return

    arg = args[0]

    if arg not in annotations:
        return

    din_type = annotations[arg]

    if not typeof(din_type, Tuple):
        return

    if not din_type.fields:
        return

    signature = inspect.formatargspec(din_type.fields, *paramspec, annotations={})

    f = FunctionMaker(name=f'{g.func.__name__}_unpack', signature=signature)

    base_func = getattr(g.func, 'alternative_to', g.func)

    body = f'''def %(name)s%(signature)s:
    {arg} = ccat({",".join(din_type.fields)})
    return {base_func.__name__}({find_invocation(base_func)})'''

    from ..lib import ccat
    closure = {'ccat': ccat}
    closure.update(get_function_context_dict(g.func))

    unpack_func = f.make(body,
                         evaldict=closure,
                         addsource=True)

    unpack_func.__kwdefaults__ = paramspec[-1]

    p = Partial(unpack_func)
    p.meta_kwds = {'definition': p}

    add_alternative(base_func, p.func)


def create_gear_definition(func, gear_resolver=None, **meta_kwds):
    if gear_resolver is None:
        gear_resolver = registry('gear/gear_dflt_resolver')

    # Add defaults from GearMetaParams registry
    for k, v in registry('gear/params/meta').items():
        if k not in meta_kwds:
            meta_kwds[k] = copy.copy(v)

    execdict = {
        'gear_resolver': gear_resolver,
        'meta_kwds': meta_kwds,
        'gear_func': func
    }
    execdict.update(get_function_context_dict(func))

    invocation = find_invocation(func)
    body = f'return gear_resolver(gear_func, meta_kwds, {invocation})'

    gear_func = FunctionMaker.create(
        obj=func,
        body=body,
        evaldict=execdict,
        addsource=True,
        extra_kwds={
            k: copy.copy(v)
            for k, v in registry('gear/params/extra').items()
        })

    functools.update_wrapper(gear_func, func)

    p = Partial(gear_func)
    meta_kwds['definition'] = p
    p.meta_kwds = meta_kwds

    create_unpacked_tuple_alternative(p)

    return p


gear = doublewrap(create_gear_definition)


class GearDecoratorPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/gear_dflt_resolver', None)
