import logging
import pprint
import ast
import textwrap
import inspect

from .ast.utils import get_function_source

logger = None


def hls_log():
    global logger
    if logger is None:
        import sys
        logger = logging.getLogger('hls')
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        logger.addHandler(h)

    return logger


def hls_enable_debug_log():
    logger = hls_log()
    logger.setLevel(logging.DEBUG)


def hls_disable_debug_log():
    logger = hls_log()
    logger.setLevel(logging.ERROR)


def hls_debug_log_enabled():
    return hls_log().getEffectiveLevel() == logging.DEBUG


def hls_debug(msg='', title=None, indent=0):
    if not hls_debug_log_enabled():
        return None

    if title is not None:
        hls_debug_header(title)

    if isinstance(msg, dict):
        msg = pprint.pformat(msg)
    elif isinstance(msg, ast.AST):
        import astpretty
        msg = astpretty.pformat(msg)
    else:
        msg = str(msg)

    if title is not None:
        msg = textwrap.indent(msg, '    ')

    hls_log().debug(textwrap.indent(msg, ' ' * indent))


def hls_debug_header(msg=''):
    hls_debug()
    hls_debug('*' * 80)
    hls_debug('*')
    for line in msg.split('\n'):
        hls_debug('* ' + line)

    hls_debug('*')
    hls_debug('*' * 80)
    hls_debug()


def print_gear_parse_intro(gear, body_ast):
    hls_debug('*' * 80)
    hls_debug_header(f'Compiling code for the gear "{gear.name}" of the type '
                     f'"{gear.definition.__name__}"')

    fn = inspect.getfile(gear.func)
    try:
        _, ln = inspect.getsourcelines(gear.func)
    except OSError:
        ln = '-'

    hls_debug(get_function_source(gear.func),
              title=f'Parsing function "{gear.func.__name__}" from "{fn}", line {ln}')

    hls_debug_header('Function body AST')

    for stmt in body_ast.body:
        hls_debug(stmt)


def print_func_parse_intro(func, body_ast):
    hls_debug('*' * 80)
    hls_debug_header(f'Compiling code for the {func}')

    fn = inspect.getfile(func)
    try:
        _, ln = inspect.getsourcelines(func)
    except OSError:
        ln = '-'

    hls_debug(get_function_source(func), title=f'Parsing function {func} from "{fn}", line {ln}')

    hls_debug_header('Function body AST')

    for stmt in body_ast.body:
        hls_debug(stmt)
