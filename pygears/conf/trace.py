import logging
import os
import sys
import textwrap
import inspect
from enum import IntEnum
from functools import partial
from traceback import (extract_stack, extract_tb, format_exception_only,
                       format_list, walk_stack, walk_tb, TracebackException)

from pygears.definitions import ROOT_DIR

from .log import register_custom_log, CustomLogger, LogPlugin, core_log
from .pdb_patch import patch_pdb, unpatch_pdb
from .registry import (Inject, PluginBase, RegistryHook, config, reg_inject,
                       registry, bind, safe_bind)


class MultiAlternativeError(Exception):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        ret = ['\n']
        for func, err_cls, err, tr in self.errors:
            ret.append('\n')
            tr_list = list(enum_traceback(tr))
            if tr_list:
                ret.extend(tr_list)
            else:
                uwrp = inspect.unwrap(
                    func, stop=(lambda f: hasattr(f, "__signature__")))
                fn = inspect.getfile(uwrp)
                _, ln = inspect.getsourcelines(uwrp)
                ret.append(f'  File "{fn}", line {ln}, in {uwrp.__name__}\n')

            # ret.append('---------------------------------\n')
            # ret.extend(traceback.format_tb(info[2]))
            # exc_msg = '\n'.join(traceback.format_exception_only(err_cls, err))
            exc_msg = register_issue(err_cls, err)
            ret.append(textwrap.indent(exc_msg, 4 * ' '))
            # ret.append('---------------------------------\n')
            # ret.append(exc_msg)
        return textwrap.indent(str(''.join(ret)), 2 * ' ')
        # return str(''.join(ret))


class TraceLevel(IntEnum):
    debug = 0
    user = 1


def set_trace_level(var, val):
    if val == TraceLevel.user:
        patch_pdb()
    else:
        unpatch_pdb()


class TraceConfigPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('trace/hooks', [])

        config.define(
            'trace/level', setter=set_trace_level, default=TraceLevel.user)

        config.define(
            'trace/ignore',
            default=[os.path.join(ROOT_DIR, d) for d in ['core', 'conf']])


def parse_trace(s, t):
    if registry('trace/level') == TraceLevel.debug:
        return s
    else:
        trace_fn = t[0].f_code.co_filename
        is_internal = any(
            trace_fn.startswith(d) for d in config['trace/ignore'])

        is_decorator_gen = trace_fn.startswith('<decorator-gen')

        if is_internal or is_decorator_gen:
            return None

        return s


@reg_inject
def register_issue(err_cls, err, issues=Inject('trace/issues')):
    tr_exc = TracebackException(err_cls, err, None)
    issue_id = len(issues)
    if isinstance(err, MultiAlternativeError):
        issue = f"{err_cls.__name__}: {tr_exc}\n"
    else:
        issue = f"{err_cls.__name__}: [{issue_id}], {tr_exc}\n"
        issues.append(err)

    return issue


def enum_traceback(tr):
    for s, t in zip(format_list(extract_tb(tr)), walk_tb(tr)):
        if parse_trace(s, t):
            yield s


def enum_stacktrace():
    for s, t in zip(format_list(extract_stack()), walk_stack(f=None)):
        if parse_trace(s, t):
            yield s


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
            register_issue(exception_type, exception))


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


class TraceLog(CustomLogger):
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
        register_custom_log('trace', cls=TraceLog)
        registry('logger/hooks').append(log_error_to_file)
        bind('trace/issues', [])
