import inspect
import textwrap


def get_function_source(func):
    try:
        source = inspect.getsource(func)
    except OSError:
        try:
            source = func.__source__
        except AttributeError:
            raise Exception(
                f'Cannot obtain source code for the gear {func.__name__}: {func}'
            )

    return textwrap.dedent(source)
