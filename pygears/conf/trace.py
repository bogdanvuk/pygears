import logging
import platform
import sys
import textwrap
import inspect
from functools import partial
from traceback import TracebackException

from .log import CustomLogger, LogPlugin, register_custom_log
from .registry import Inject, inject, reg

from .trace_format import enum_traceback, TraceLevel, enum_stacktrace


def gear_definition_location(func):
    uwrp = inspect.unwrap(func, stop=(lambda f: hasattr(f, "__signature__")))
    fn = inspect.getfile(uwrp)

    ln = 1
    lines = None
    while fn.startswith('<decorator'):
        if hasattr(uwrp, 'definition'):
            uwrp = uwrp.definition
        elif hasattr(uwrp, 'alternative_to'):
            uwrp = uwrp.alternative_to
        else:
            break

        fn = inspect.getfile(uwrp)

    try:
        lines, ln = inspect.getsourcelines(uwrp)
    except OSError:
        pass

    return uwrp, fn, ln, lines


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
                funcdef, fn, ln, _ = gear_definition_location(func)

                ret.append(
                    f'  File "{fn}", line {ln}, in {funcdef.__name__}\n')

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
    reg['trace/hooks'].append(partial(hook, *args, **kwds))


def log_exception(exception):
    exception_type = type(exception)
    tr = exception.__traceback__

    from pygears.conf.log import LogException
    print_traceback = (exception_type is not LogException)
    if not print_traceback:
        print_traceback = reg[f'logger/{exception.name}/print_traceback']
    if print_traceback:
        for s in enum_traceback(tr):
            logging.getLogger('trace').error(s[:-1])

    logging.getLogger('trace').error(register_issue(exception_type, exception))


def pygears_excepthook(exception_type,
                       exception,
                       tr,
                       debug_hook=sys.excepthook):

    for hook in reg['trace/hooks']:
        try:
            hook()
        except Exception:
            pass

    if reg['trace/level'] == TraceLevel.debug:
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
def stack_trace(name,
                verbosity,
                message,
                stack_traceback_fn=Inject('logger/stack_traceback_fn')):
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
        reg['logger/hooks'].append(log_error_to_file)
        reg['trace/issues'] = []


# -*- coding: utf-8 -*-
"""
    jinja2.debug
    ~~~~~~~~~~~~

    Implements the debug interface for Jinja.  This module does some pretty
    ugly stuff with the Python traceback system in order to achieve tracebacks
    with correct line numbers, locals and contents.

    :copyright: (c) 2017 by the Jinja Team.
    :license: BSD, see LICENSE for more details.
"""
import sys
import traceback
from types import TracebackType, CodeType

class TraceException(Exception):
    """Raised to tell the user that there is a problem with the template."""

    def __init__(self, message, lineno=None, name=None, filename=None):
        Exception.__init__(self, message)
        self.lineno = lineno
        self.name = name
        self.filename = filename
        self.source = None
        self.message = message

    def __reduce__(self):
        # https://bugs.python.org/issue1692335 Exceptions that take
        # multiple required arguments have problems with pickling.
        # Without this, raises TypeError: __init__() missing 1 required
        # positional argument: 'lineno'
        return self.__class__, (self.message, self.lineno, self.name, self.filename)

# on pypy we can take advantage of transparent proxies
try:
    from __pypy__ import tproxy
except ImportError:
    tproxy = None


# how does the raise helper look like?
try:
    exec("raise TypeError, 'foo'")
except SyntaxError:
    raise_helper = 'raise __jinja_exception__[1]'
except TypeError:
    raise_helper = 'raise __jinja_exception__[0], __jinja_exception__[1]'


class TracebackFrameProxy(object):
    """Proxies a traceback frame."""

    def __init__(self, tb):
        self.tb = tb
        self._tb_next = None

    @property
    def tb_next(self):
        return self._tb_next

    def set_next(self, next):
        if tb_set_next is not None:
            try:
                tb_set_next(self.tb, next and next.tb or None)
            except Exception:
                # this function can fail due to all the hackery it does
                # on various python implementations.  We just catch errors
                # down and ignore them if necessary.
                pass
        self._tb_next = next

    @property
    def is_jinja_frame(self):
        return '__jinja_template__' in self.tb.tb_frame.f_globals

    def __getattr__(self, name):
        return getattr(self.tb, name)


def make_frame_proxy(frame):
    proxy = TracebackFrameProxy(frame)
    if tproxy is None:
        return proxy
    def operation_handler(operation, *args, **kwargs):
        if operation in ('__getattribute__', '__getattr__'):
            return getattr(proxy, args[0])
        elif operation == '__setattr__':
            proxy.__setattr__(*args, **kwargs)
        else:
            return getattr(proxy, operation)(*args, **kwargs)
    return tproxy(TracebackType, operation_handler)


class ProcessedTraceback(object):
    """Holds a Jinja preprocessed traceback for printing or reraising."""

    def __init__(self, exc_type, exc_value, frames):
        assert frames, 'no frames for this traceback?'
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.frames = frames

        # newly concatenate the frames (which are proxies)
        prev_tb = None
        for tb in self.frames:
            if prev_tb is not None:
                prev_tb.set_next(tb)
            prev_tb = tb
        prev_tb.set_next(None)

    def render_as_text(self, limit=None):
        """Return a string with the traceback."""
        lines = traceback.format_exception(self.exc_type, self.exc_value,
                                           self.frames[0], limit=limit)
        return ''.join(lines).rstrip()

    def render_as_html(self, full=False):
        """Return a unicode string with the traceback as rendered HTML."""
        from jinja2.debugrenderer import render_traceback
        return u'%s\n\n<!--\n%s\n-->' % (
            render_traceback(self, full=full),
            self.render_as_text().decode('utf-8', 'replace')
        )

    @property
    def is_template_syntax_error(self):
        """`True` if this is a template syntax error."""
        return isinstance(self.exc_value, TraceException)

    @property
    def exc_info(self):
        """Exception info tuple with a proxy around the frame objects."""
        return self.exc_type, self.exc_value, self.frames[0]

    @property
    def standard_exc_info(self):
        """Standard python exc_info for re-raising"""
        tb = self.frames[0]
        # the frame will be an actual traceback (or transparent proxy) if
        # we are on pypy or a python implementation with support for tproxy
        if type(tb) is not TracebackType:
            tb = tb.tb
        return self.exc_type, self.exc_value, tb


def make_traceback(exc_info, source_hint=None):
    """Creates a processed traceback object from the exc_info."""
    exc_type, exc_value, tb = exc_info
    if isinstance(exc_value, TraceException):
        exc_info = translate_syntax_error(exc_value, source_hint)
        initial_skip = 0
    else:
        initial_skip = 1
    return translate_exception(exc_info, initial_skip)


def translate_syntax_error(error, source=None):
    """Rewrites a syntax error to please traceback systems."""
    error.source = source
    error.translated = True
    exc_info = (error.__class__, error, None)
    filename = error.filename
    if filename is None:
        filename = '<unknown>'
    return fake_exc_info(exc_info, filename, error.lineno)


def translate_exception(exc_info, initial_skip=0):
    """If passed an exc_info it will automatically rewrite the exceptions
    all the way down to the correct line numbers and frames.
    """
    tb = exc_info[2]
    frames = []

    # skip some internal frames if wanted
    for x in range(initial_skip):
        if tb is not None:
            tb = tb.tb_next
    initial_tb = tb

    while tb is not None:
        frames.append(make_frame_proxy(tb))
        tb = tb.tb_next

    return ProcessedTraceback(exc_info[0], exc_info[1], frames)


def fake_exc_info(exc_info, filename, lineno):
    """Helper for `translate_exception`."""
    exc_type, exc_value, tb = exc_info
    locals = {}

    # assamble fake globals we need
    globals = {
        '__name__':             filename,
        '__file__':             filename,
        '__jinja_exception__':  exc_info[:2],
    }

    # and fake the exception
    code = compile('\n' * (lineno - 1) + raise_helper, filename, 'exec')

    # if it's possible, change the name of the code.  This won't work
    # on some python environments such as google appengine
    try:
        if tb is None:
            location = 'template'
        else:
            function = tb.tb_frame.f_code.co_name
            if function == 'root':
                location = 'top-level template code'
            elif function.startswith('block_'):
                location = 'block "%s"' % function[6:]
            else:
                location = 'template'

        code = CodeType(0, code.co_kwonlyargcount,
                        code.co_nlocals, code.co_stacksize,
                        code.co_flags, code.co_code, code.co_consts,
                        code.co_names, code.co_varnames, filename,
                        location, code.co_firstlineno,
                        code.co_lnotab, (), ())
    except Exception as e:
        pass

    # execute the code and catch the new traceback
    try:
        exec(code, globals, locals)
    except:
        exc_info = sys.exc_info()
        new_tb = exc_info[2].tb_next

    # return without this frame
    return exc_info[:2] + (new_tb,)


if sys.version_info >= (3, 7):
    # tb_next is directly assignable as of Python 3.7
    def tb_set_next(tb, tb_next):
        tb.tb_next = tb_next
        return tb

elif platform.python_implementation() == "PyPy":
    # PyPy might have special support, and won't work with ctypes.
    try:
        import tputil
    except ImportError:
        # Without tproxy support, use the original traceback.
        def tb_set_next(tb, tb_next):
            return tb

    else:
        # With tproxy support, create a proxy around the traceback that
        # returns the new tb_next.
        def tb_set_next(tb, tb_next):
            def controller(op):
                if op.opname == "__getattribute__" and op.args[0] == "tb_next":
                    return tb_next

                return op.delegate()

            return tputil.make_proxy(controller, obj=tb)


else:
    # Use ctypes to assign tb_next at the C level since it's read-only
    # from Python.
    import ctypes

    class _CTraceback(ctypes.Structure):
        _fields_ = [
            # Extra PyObject slots when compiled with Py_TRACE_REFS.
            ("PyObject_HEAD", ctypes.c_byte * object().__sizeof__()),
            # Only care about tb_next as an object, not a traceback.
            ("tb_next", ctypes.py_object),
        ]

    def tb_set_next(tb, tb_next):
        c_tb = _CTraceback.from_address(id(tb))

        # Clear out the old tb_next.
        if tb.tb_next is not None:
            c_tb_next = ctypes.py_object(tb.tb_next)
            c_tb.tb_next = ctypes.py_object()
            ctypes.pythonapi.Py_DecRef(c_tb_next)

        # Assign the new tb_next.
        if tb_next is not None:
            c_tb_next = ctypes.py_object(tb_next)
            ctypes.pythonapi.Py_IncRef(c_tb_next)
            c_tb.tb_next = c_tb_next

        return tb
