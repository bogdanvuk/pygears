import os
from enum import IntEnum
from traceback import (extract_stack, extract_tb, format_list, walk_stack,
                       walk_tb)

from .registry import registry


class ErrReportLevel(IntEnum):
    debug = 0
    user = 1


def parse_trace(s, t):
    if registry('err/level') == ErrReportLevel.debug:
        yield s
    else:
        is_internal = t[0].f_code.co_filename.startswith(
            os.path.dirname(__file__))
        is_boltons = 'boltons' in t[0].f_code.co_filename
        if not is_internal and not is_boltons:
            yield s


def enum_traceback(tr):
    for s, t in zip(format_list(extract_tb(tr)), walk_tb(tr)):
        yield from parse_trace(s, t)


def enum_stacktrace():
    for s, t in zip(format_list(extract_stack()), walk_stack(f=None)):
        yield from parse_trace(s, t)
