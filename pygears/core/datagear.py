import inspect
from pygears import reg, Intf
from pygears.core.gear_decorator import create_gear_definition
from pygears.core.gear_decorator import FunctionMaker
from pygears.core.util import doublewrap, get_function_context_dict
from pygears.core.util import is_standard_func
from pygears.util.utils import gather


def is_datagear(func):
    return hasattr(func, 'exec')


def get_datagear_func(func):
    return func.exec


# TODO: "outnames" not working
@doublewrap
def datagear(func, **meta_kwds):
    if not is_standard_func(func):
        raise Exception('Only regular functions can be converted to a @datagear.')

    paramspec = inspect.getfullargspec(func)

    invocation = ['*_data']

    for name in paramspec.kwonlyargs:
        invocation.append(f'{name}={name}')

    body = f'''async with gather({",".join(paramspec.args)}) as _data:
        yield datafunc({",".join(invocation)})'''

    # TODO: Small optimization point to avoid async context manager. This needs to be supported by the compiler
    # invocation = [f'await {a}.pull()' for a in paramspec.args]
    # for name in paramspec.kwonlyargs:
    #     invocation.append(f'{name}={name}')

    # ack = ','.join(f'{a}.ack()' for a in paramspec.args)

    # body = f'''
    # yield datafunc({",".join(invocation)})
    # {ack}
    # '''

    execdict = {'datafunc': func, 'gather': gather}
    execdict.update(get_function_context_dict(func))

    gear_func = FunctionMaker.create(obj=func,
                                     body=body,
                                     evaldict=execdict,
                                     isasync=True,
                                     addsource=True)
    gear_func.exec = func

    return create_gear_definition(gear_func)
