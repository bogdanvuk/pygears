import logging
import os
import sys
from enum import IntEnum
from functools import partial
from traceback import (extract_stack, extract_tb, format_exception_only,
                       format_list, walk_stack, walk_tb)

from pygears.definitions import ROOT_DIR

from .log import CustomLog, LogPlugin, core_log
from .pdb_patch import patch_pdb, unpatch_pdb
from .registry import (Inject, PluginBase, RegistryHook, config, reg_inject,
                       registry)


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
        cls.registry['trace'] = TraceConfig(level=TraceLevel.user)
        cls.registry['trace']['hooks'] = []

        config.define(
            'trace/ignore',
            default=[os.path.join(ROOT_DIR, d) for d in ['core', 'conf']])


def parse_trace(s, t):
    if registry('trace/level') == TraceLevel.debug:
        yield s
    else:
        trace_fn = t[0].f_code.co_filename
        is_internal = any(
            trace_fn.startswith(d) for d in config['trace/ignore'])

        is_boltons = 'boltons' in trace_fn
        if not is_internal and not is_boltons:
            yield s


def enum_traceback(tr):
    print("Trace ignores")
    print(config['trace/ignore'])

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
                logging.getLogger('trace').error(s[:-1])

        logging.getLogger('trace').error(
            format_exception_only(exception_type, exception)[0])


@reg_inject
def stack_trace(name,
                verbosity,
                message,
                stack_traceback_fn=Inject('logger/stack_traceback_fn')):
    with open(stack_traceback_fn, 'a') as f:
        delim = '-' * 50 + '\n'
        f.write(delim)
        f.write(f'{name} [{verbosity.upper()}] {message}\n\n')
        tr = ''
        exc_type, exc_value, exc_traceback = sys.exc_info()
        for s in enum_stacktrace():
            tr += s
        f.write(tr)
        f.write(delim)


def log_error_to_file(name, severity, msg):
    if severity in ['error', 'warning']:
        stack_trace(name, severity, msg)


class TraceLog(CustomLog):
    # def __init__(self, name, verbosity=logging.INFO):
    #     super().__init__(name, verbosity)

    #     # change default for error
    #     bind('logger/sim/error', 'exception')
    #     bind('logger/sim/print_traceback', False)

    def get_format(self):
        return logging.Formatter('%(message)s')

    def get_filter(self):
        return None


class TracePlugin(LogPlugin):
    @classmethod
    def bind(cls):
        TraceLog('trace')
        registry('logger/hooks').append(log_error_to_file)
