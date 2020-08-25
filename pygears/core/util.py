import inspect
from functools import wraps


def doublewrap(f):
    '''
    a decorator decorator, allowing the decorator to be used as:
    @decorator(with, arguments, and=kwds)
    or
    @decorator
    '''
    @wraps(f)
    def new_dec(*args, **kwds):
        if len(args) == 1 and len(kwds) == 0 and callable(args[0]):
            # actual decorated function
            return f(args[0])
        else:
            # decorator arguments
            return lambda realf: f(realf, *args, **kwds)

    return new_dec


def perpetum(func, *args, **kwds):
    while True:
        yield func(*args, **kwds)


def is_standard_func(func):
    return not (inspect.iscoroutinefunction(func) or inspect.isgeneratorfunction(func)
                or is_async_gen(func))


def is_async_gen(func):
    return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)


def get_function_context_dict(func):
    if func.__closure__ is None:
        return func.__globals__

    context = {}
    context.update(func.__globals__)

    for name, cell in zip(func.__code__.co_freevars, func.__closure__):
        try:
            context[name] = cell.cell_contents
        except ValueError:
            # Cell is empty
            pass

    return context
