from pygears.registry import registry, PluginBase
from functools import partial
from enum import IntEnum
from traceback import extract_tb, format_list, walk_tb
from traceback import format_exception_only
import os
import sys


class ErrReportLevel(IntEnum):
    debug = 0
    user = 1


class ErrReportPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['ErrReportLevel'] = ErrReportLevel.user
        # cls.registry['ErrReportLevel'] = ErrReportLevel.debug
        cls.registry['ExitHooks'] = []


def register_exit_hook(hook, *args, **kwds):
    registry('ExitHooks').append(partial(hook, *args, **kwds))


def enum_traceback(tr):
    for s, t in zip(format_list(extract_tb(tr)), walk_tb(tr)):
        if registry("ErrReportLevel") == ErrReportLevel.debug:
            yield s
        else:
            is_internal = t[0].f_code.co_filename.startswith(
                os.path.dirname(__file__))
            is_boltons = 'boltons' in t[0].f_code.co_filename
            if not is_internal and not is_boltons:
                yield s


def pygears_excepthook(exception_type,
                       exception,
                       tr,
                       debug_hook=sys.excepthook):

    for hook in registry('ExitHooks'):
        try:
            hook()
        except:
            pass

    if registry("ErrReportLevel") == ErrReportLevel.debug:
        debug_hook(exception_type, exception, tr)
    else:
        from pygears.util.print_hier import print_hier
        from pygears import find

        try:
            print_hier(find('/'))
        except Exception as e:
            pass

        for s in enum_traceback(tr):
            print(s, end='')

        print(format_exception_only(exception_type, exception)[0])
