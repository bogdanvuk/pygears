import os
import sys

from enum import IntEnum
from traceback import (extract_stack, extract_tb, format_list, walk_stack,
                       walk_tb)
from functools import partial
from traceback import format_exception_only

from .pdb_patch import patch_pdb, unpatch_pdb
from .registry import PluginBase, RegistryHook, registry


class TraceLevel(IntEnum):
    debug = 0
    user = 1


class TraceConfig(RegistryHook):
    def _set_level(self, val):
        if val == TraceLevel.user:
            patch_pdb()
        else:
            unpatch_pdb()


class TraceConfigPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['trace'] = TraceConfig(level=TraceLevel.debug)
        cls.registry['trace']['hooks'] = []


def parse_trace(s, t):
    if registry('trace/level') == TraceLevel.debug:
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


def register_exit_hook(hook, *args, **kwds):
    registry('trace/hooks').append(partial(hook, *args, **kwds))


def pygears_excepthook(exception_type,
                       exception,
                       tr,
                       debug_hook=sys.excepthook):

    for hook in registry('trace/hooks'):
        try:
            hook()
        except:
            pass

    if registry('trace/level') == TraceLevel.debug:
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
        from pygears.conf.log import LogException
        print_traceback = (exception_type is not LogException)
        if not print_traceback:
            print_traceback = registry(
                f'logger/{exception.name}/print_traceback')
        if print_traceback:
            for s in enum_traceback(tr):
                print(s, end='')

        print(format_exception_only(exception_type, exception)[0])
