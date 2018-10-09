import os
import sys
from enum import IntEnum
from functools import partial
from traceback import (extract_stack, extract_tb, format_exception_only,
                       format_list, walk_stack, walk_tb)

from pygears.registry import PluginBase, registry


class ErrReportLevel(IntEnum):
    debug = 0
    user = 1


class ErrReportPlugin(PluginBase):
    @classmethod
    def bind(cls):
        # cls.registry['ErrReportLevel'] = ErrReportLevel.user
        # from .pdb_patch import patch_pdb
        # patch_pdb()

        cls.registry['ErrReportLevel'] = ErrReportLevel.debug
        cls.registry['ExitHooks'] = []


def register_exit_hook(hook, *args, **kwds):
    registry('ExitHooks').append(partial(hook, *args, **kwds))


def parse_trace(s, t):
    if registry("ErrReportLevel") == ErrReportLevel.debug:
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

        # print traceback for LogException only if appropriate
        # 'print_traceback' in registry is set
        from pygears.core.log import LogException, registry_log_name
        print_traceback = (exception_type is not LogException)
        if not print_traceback:
            print_traceback = registry(
                registry_log_name.substitute(
                    name=exception.name))['print_traceback']
        if print_traceback:
            for s in enum_traceback(tr):
                print(s, end='')

        print(format_exception_only(exception_type, exception)[0])
