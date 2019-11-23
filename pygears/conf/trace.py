import logging
import sys
import textwrap
import inspect
from functools import partial
from traceback import TracebackException

from .log import CustomLogger, LogPlugin, register_custom_log
from .registry import Inject, bind, inject, registry

from .trace_format import enum_traceback, TraceLevel, enum_stacktrace


def gear_definition_location(func):
    uwrp = inspect.unwrap(func, stop=(lambda f: hasattr(f, "__signature__")))
    fn = inspect.getfile(uwrp)

    ln = '-'
    if fn.startswith('<decorator'):
        if hasattr(uwrp, 'definition'):
            uwrp = uwrp.definition
        elif hasattr(uwrp, 'alternative_to'):
            uwrp = uwrp.alternative_to

        fn = inspect.getfile(uwrp)
        _, ln = inspect.getsourcelines(uwrp)
    else:
        try:
            _, ln = inspect.getsourcelines(uwrp)
        except OSError:
            pass

    return uwrp, fn, ln


class MultiAlternativeError(Exception):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        ret = ['\n']
        for err_pack in self.errors:
            if err_pack is None:
                continue

            func, err_cls, err, tr = err_pack

            ret.append('\n')
            tr_list = None if not tr else list(enum_traceback(tr))
            if tr_list:
                ret.extend(tr_list)
            else:
                funcdef, fn, ln = gear_definition_location(func)

                ret.append(f'  File "{fn}", line {ln}, in {funcdef.__name__}\n')

            exc_msg = register_issue(err_cls, err)
            ret.append(textwrap.indent(exc_msg, 4 * ' '))

        return textwrap.indent(str(''.join(ret)), 2 * ' ')


@inject
def register_issue(err_cls, err, issues=Inject('trace/issues')):
    tr_exc = TracebackException(err_cls, err, None)
    issue_id = len(issues)
    if isinstance(err, MultiAlternativeError):
        issue = f"{err_cls.__name__}: {tr_exc}\n"
    else:
        issue = f"{err_cls.__name__}: [{issue_id}], {tr_exc}\n"
        issues.append(err)

    return issue


def register_exit_hook(hook, *args, **kwds):
    registry('trace/hooks').append(partial(hook, *args, **kwds))


def log_exception(exception):
    exception_type = type(exception)
    tr = exception.__traceback__

    from pygears.conf.log import LogException
    print_traceback = (exception_type is not LogException)
    if not print_traceback:
        print_traceback = registry(f'logger/{exception.name}/print_traceback')
    if print_traceback:
        for s in enum_traceback(tr):
            logging.getLogger('trace').error(s[:-1])

    logging.getLogger('trace').error(register_issue(exception_type, exception))


def pygears_excepthook(exception_type, exception, tr, debug_hook=sys.excepthook):

    for hook in registry('trace/hooks'):
        try:
            hook()
        except Exception:
            pass

    if registry('trace/level') == TraceLevel.debug:
        debug_hook(exception_type, exception, tr)
    else:
        from pygears.util.print_hier import print_hier
        from pygears import find

        try:
            print_hier(find('/'))
        except Exception:
            pass

        log_exception(exception.with_traceback(tr))


@inject
def stack_trace(
        name, verbosity, message, stack_traceback_fn=Inject('logger/stack_traceback_fn')):
    with open(stack_traceback_fn, 'a') as f:
        delim = '-' * 50 + '\n'
        f.write(delim)
        f.write(f'{name} [{verbosity.upper()}] {message}\n\n')
        tr = ''
        for s in enum_stacktrace():
            tr += s
        f.write(tr)
        f.write(delim)


def log_error_to_file(name, severity, msg):
    if severity in ['error', 'warning']:
        stack_trace(name, severity, msg)


class TraceLog(CustomLogger):
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
