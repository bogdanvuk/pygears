import inspect
from pygears.core.gear_decorator import create_gear_definition
from pygears.core.gear_decorator import FunctionMaker
from pygears.core.util import doublewrap, get_function_context_dict
from pygears.util.utils import gather


@doublewrap
def datagear(func, **meta_kwds):
    paramspec = inspect.getfullargspec(func)

    body = f'''async with gather({",".join(paramspec.args)}) as data:
        res = datafunc(*data)
        yield res'''

    execdict = {'datafunc': func, 'gather': gather}
    execdict.update(get_function_context_dict(func))

    gear_func = FunctionMaker.create(obj=func,
                                     body=body,
                                     evaldict=execdict,
                                     isasync=True,
                                     addsource=True)

    return create_gear_definition(gear_func, hdl={'compile': True})
