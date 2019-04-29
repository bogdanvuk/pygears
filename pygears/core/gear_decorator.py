import copy
import functools
import inspect

from pygears.conf import Inject, inject, registry, PluginBase, safe_bind

from .funcutils import FunctionMaker
from .partial import Partial
from .util import doublewrap


def alternative(*base_gear_defs):
    def gear_decorator(gear_def):
        for d in base_gear_defs:
            alternatives = getattr(d.func, 'alternatives', [])
            alternatives.append(gear_def.func)
            gear_func = gear_def.func.__wrapped__
            gear_func_to = d.func.__wrapped__

            gear_func.alternative_to = gear_func_to
            gear_func_to.alternatives = alternatives
            d.func.alternatives = alternatives
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


@doublewrap
def gear(func, gear_resolver=None, **meta_kwds):

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
    execdict.update(func.__globals__)

    invocation = find_invocation(func)
    body = f'return gear_resolver(gear_func, meta_kwds, {invocation})'

    gear_func = FunctionMaker.create(
        obj=func,
        body=body,
        evaldict=execdict,
        addsource=True,
        extra_kwds=registry('gear/params/extra'))

    functools.update_wrapper(gear_func, func)

    p = Partial(gear_func)
    meta_kwds['definition'] = p
    p.meta_kwds = meta_kwds

    return p


class GearDecoratorPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/gear_dflt_resolver', None)
