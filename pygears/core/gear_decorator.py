import copy
import functools
import inspect
import pygears

from pygears.conf import Inject, inject, reg, PluginBase
from pygears.core.graph import get_producer_port
from pygears.typing import Tuple, typeof
from pygears import module
from pygears.core.util import is_async_gen

from .funcutils import FunctionMaker
from .partial import Partial
from .util import doublewrap, get_function_context_dict


def add_alternative(base, alter):
    alternatives = getattr(base, 'alternatives', [])
    alternatives.append(alter)
    gear_func = getattr(alter, '__wrapped__', alter)

    if hasattr(gear_func, 'alternatives'):
        alternatives.extend(gear_func.alternatives)

    gear_func_to = getattr(base, '__wrapped__', base)

    gear_func.alternative_to = gear_func_to
    gear_func_to.alternatives = alternatives

    if hasattr(gear_func, 'meta_kwds'):
        gear_func.meta_kwds['__base__'] = gear_func_to

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


def formatannotation(annotation, base_module=None):
    if getattr(annotation, '__module__', '').startswith('pygears.typing'):
        return repr(annotation)
    if getattr(annotation, '__module__', None) == 'typing':
        return repr(annotation).replace('typing.', '')
    if isinstance(annotation, type):
        if annotation.__module__ in ('builtins', base_module):
            return annotation.__qualname__
        return annotation.__module__ + '.' + annotation.__qualname__
    return repr(annotation)


def formatargspec(args,
                  varargs=None,
                  varkw=None,
                  defaults=None,
                  kwonlyargs=(),
                  kwonlydefaults={},
                  annotations={},
                  formatarg=str,
                  formatvarargs=lambda name: '*' + name,
                  formatvarkw=lambda name: '**' + name,
                  formatvalue=lambda value: '=' + repr(value),
                  formatreturns=lambda text: ' -> ' + text,
                  formatannotation=formatannotation):
    """Format an argument spec from the values returned by getfullargspec.

    The first seven arguments are (args, varargs, varkw, defaults,
    kwonlyargs, kwonlydefaults, annotations).  The other five arguments
    are the corresponding optional formatting functions that are called to
    turn names and values into strings.  The last argument is an optional
    function to format the sequence of arguments.

    Deprecated since Python 3.5: use the `signature` function and `Signature`
    objects.
    """
    def formatargandannotation(arg):
        result = formatarg(arg)
        if arg in annotations:
            result += ': ' + formatannotation(annotations[arg])
        return result

    specs = []
    if defaults:
        firstdefault = len(args) - len(defaults)
    for i, arg in enumerate(args):
        spec = formatargandannotation(arg)
        if defaults and i >= firstdefault:
            spec = spec + formatvalue(defaults[i - firstdefault])
        specs.append(spec)
    if varargs is not None:
        specs.append(formatvarargs(formatargandannotation(varargs)))
    else:
        if kwonlyargs:
            specs.append('*')
    if kwonlyargs:
        for kwonlyarg in kwonlyargs:
            spec = formatargandannotation(kwonlyarg)
            if kwonlydefaults and kwonlyarg in kwonlydefaults:
                spec += formatvalue(kwonlydefaults[kwonlyarg])
            specs.append(spec)
    if varkw is not None:
        specs.append(formatvarkw(formatargandannotation(varkw)))
    result = '(' + ', '.join(specs) + ')'
    if 'return' in annotations:
        result += formatreturns(formatannotation(annotations['return']))
    return result


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

    unpack_annot = {name: dtype for name, dtype in zip(din_type.fields, din_type.args)}

    signature = formatargspec(din_type.fields, *paramspec)

    f = FunctionMaker(name=f'__{g.func.__name__}_unpack__', signature=signature)

    f.annotations = unpack_annot

    base_func = g.func

    while (hasattr(base_func, 'alternative_to')):
        base_func = base_func.alternative_to

    body = f'''def %(name)s%(signature)s:
    {arg} = ccat({",".join(din_type.fields)})
    try:
        return __{base_func.__name__}({find_invocation(base_func)}, __no_unpack_alt__=True)
    except Exception as e:
        gear_inst = module().child[-1]
        gear_inst.parent.child.remove(gear_inst)
        for port in gear_inst.in_ports:
            if port.basename not in gear_inst.const_args:
                port.producer.consumers.remove(port)
            else:
                gear_inst.parent.child.remove(get_producer_port(port).gear)
        raise e
    '''

    from ..lib.ccat import ccat
    closure = {'ccat': ccat, f'__{base_func.__name__}': g, 'pygears': pygears, 'module': module}
    closure.update(get_function_context_dict(g.func))

    unpack_func = f.make(body, evaldict=closure, addsource=True)

    unpack_func.__kwdefaults__ = paramspec[-1]

    add_alternative(base_func, unpack_func)


def infer_outnames(annotations, meta_kwds):
    outnames = None
    if "return" in annotations:
        if isinstance(annotations['return'], dict):
            outnames = tuple(annotations['return'].keys())

    if not outnames:
        outnames = meta_kwds['outnames']

    if not outnames:
        outnames = []

    return outnames


def create_gear_definition(func, gear_resolver=None, **meta_kwds):

    if inspect.isgeneratorfunction(func):
        raise Exception(f'Generator function {func} cannot be used as a module. PyGears currently only supports regular functions'
                        f' or async generators')

    if gear_resolver is None:
        gear_resolver = reg['gear/gear_dflt_resolver']

    # Add defaults from GearMetaParams registry
    for k, v in reg['gear/params/meta'].items():
        if k not in meta_kwds:
            meta_kwds[k] = copy.copy(v)

    execdict = {'gear_resolver': gear_resolver, 'gear_func': func}
    execdict.update(get_function_context_dict(func))

    invocation = find_invocation(func)
    body = f'return gear_resolver(gear_func, {invocation})'

    gear_func = FunctionMaker.create(
        obj=func,
        body=body,
        evaldict=execdict,
        addsource=True,
        extra_kwds={k: copy.copy(v)
                    for k, v in reg['gear/params/extra'].items()})

    functools.update_wrapper(gear_func, func)

    p = Partial(gear_func)

    meta_kwds['definition'] = p
    meta_kwds['outnames'] = infer_outnames(func.__annotations__, meta_kwds)
    func.meta_kwds = meta_kwds

    create_unpacked_tuple_alternative(p)

    return p


gear = doublewrap(create_gear_definition)


class GearDecoratorPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['gear/gear_dflt_resolver'] = None
