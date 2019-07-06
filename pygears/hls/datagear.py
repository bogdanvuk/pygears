import copy
import inspect
from pygears.core.gear_decorator import create_gear_definition
from pygears.core.gear_decorator import find_invocation, FunctionMaker
from pygears.core.util import doublewrap
from pygears import registry
import functools


@doublewrap
def datagear(func, **meta_kwds):
    paramspec = inspect.getfullargspec(func)

    body = f'''async with gather({",".join(paramspec.args)}) as data:
        res = datafunc(*data)
        yield res'''

    execdict = {'datafunc': func}
    gear_func = FunctionMaker.create(obj=func,
                                     body=body,
                                     evaldict=execdict,
                                     isasync=True,
                                     addsource=True)
    return create_gear_definition(gear_func, hdl={'compile': True})
