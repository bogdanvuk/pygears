from functools import wraps


def func_module(cls, func, *meta_args, **meta_kwds):
    @wraps(func)
    def wrapper(*args, **kwds):
        return cls(func, meta_args, meta_kwds, *args, **kwds)

    return wrapper


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
