import copy
from pygears.core.gear_decorator import create_gear_definition
from pygears.core.gear_decorator import find_invocation, FunctionMaker
from pygears.core.util import doublewrap
from pygears import registry
import functools


@doublewrap
def datagear(func, **meta_kwds):
    body = '''async with x as data:
        res = datafunc(data)
        yield res'''

    execdict = {'datafunc': func}
    gear_func = FunctionMaker.create(obj=func,
                                     body=body,
                                     evaldict=execdict,
                                     isasync=True,
                                     addsource=True)
    return create_gear_definition(gear_func, hdl={'compile': True})

    # execdict = {
    #     'create_gear_definition': create_gear_definition,
    #     'gear_func': wrap_func
    # }
    # execdict.update(func.__globals__)

    # invocation = find_invocation(func)
    # body = f'return create_gear_definition(gear_func, meta_kwds, {invocation})'

    # gear_func = FunctionMaker.create(
    #     obj=func,
    #     body=body,
    #     evaldict=execdict,
    #     addsource=True,
    #     extra_kwds={
    #         k: copy.copy(v)
    #         for k, v in registry('gear/params/extra').items()
    #     })

    # functools.update_wrapper(gear_func, func)
