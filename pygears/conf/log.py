"""This module implements various logging facilities for the PyGears framework.
It is a wrapper around standard Python `logging
<https://docs.python.org/library/logging.html>`__ but provides some additional
features like:

- automatic exception raising when logging errors and warnings,
- customized stack trace printing
- logging to temporary files
- integration with PyGears registry for configuration

To register a new logger create a :class:`CustomLog` instance by specifying the
logger name and the default logging level:

>>> CustomLog('core', log.WARNING)

.. _levels:

Logging Levels
--------------

The numeric values of logging levels are given in the following table.

+--------------+---------------+
| Level        | Numeric value |
+==============+===============+
| ``CRITICAL`` | 50            |
+--------------+---------------+
| ``ERROR``    | 40            |
+--------------+---------------+
| ``WARNING``  | 30            |
+--------------+---------------+
| ``INFO``     | 20            |
+--------------+---------------+
| ``DEBUG``    | 10            |
+--------------+---------------+
| ``NOTSET``   | 0             |
+--------------+---------------+

"""

import os
import copy
import logging
from logging import INFO, WARNING, ERROR, DEBUG
import sys
import tempfile
from functools import partial

from .registry import PluginBase, safe_bind, registry, set_cb
from .trace import enum_stacktrace


def set_log_level(name, level):
    log = logging.getLogger(name)
    if log.level != level:
        log.setLevel(level)
        for h in log.handlers:
            h.setLevel(level)
    conf_log().info(f'Setting log level {name}, {level}')


class LogException(Exception):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


class LogWrap:
    def __init__(self, logger):
        self.logger = logger
        self.name = logger.name

    def severity_action(self, severity, message):
        log_cfg = registry('logger')[self.name]
        if log_cfg[severity]['exception']:
            raise LogException(message, self.name)
        elif log_cfg[severity]['debug']:
            import pdb
            pdb.set_trace()

    def stack_trace(self, verbosity, message):
        stack_traceback_fn = registry('logger/stack_traceback_fn')
        with open(stack_traceback_fn, 'a') as f:
            delim = '-' * 50 + '\n'
            f.write(delim)
            f.write(f'{self.name} [{verbosity.upper()}] {message}\n\n')
            tr = ''
            exc_type, exc_value, exc_traceback = sys.exc_info()
            for s in enum_stacktrace():
                tr += s
            f.write(tr)
            f.write(delim)

    def warning(self, message, *args, **kws):
        if self.logger.isEnabledFor(WARNING):
            severity = 'warning'
            self.logger._log(WARNING, message, args, **kws)
            self.stack_trace(severity, message)
            self.severity_action(severity, message)

    def error(self, message, *args, **kws):
        if self.logger.isEnabledFor(logging.ERROR):
            severity = 'error'
            self.logger._log(logging.ERROR, message, args, **kws)
            self.stack_trace(severity, message)
            self.severity_action(severity, message)


class LogFmtFilter(logging.Filter):
    def filter(self, record):
        record.stack_file = ''
        record.err_file = ''

        if record.levelno > INFO:
            stack_traceback_fn = registry('logger/stack_traceback_fn')
            if os.path.exists(stack_traceback_fn):
                stack_num = sum(1 for line in open(stack_traceback_fn))
            else:
                stack_num = 0
            record.stack_file = f'\n\t File "{stack_traceback_fn}", line {stack_num}, for stacktrace'
            record.err_file = f'\n\t File "{record.pathname}", line {record.lineno}, in {record.funcName}'

        return True


class CustomLog:
    '''PyGears integrated logger class.

    Args:
        name: logger name
        verbosity: default logging level:

    CustomLog instances are customizable via :samp:`logger/{logger_name}`
    :ref:`registry <registry:registry>` subtree. The logger instance registry subtree
    contains the following configuration variables:

    - ``level`` (int): All messages that are logged with a verbosity level
      below this configured ``level`` value will be discarded. See
      :ref:`levels` for a list of levels.
    - ``warning``: Configuration for logging at ``WARNING`` level

      - ``warning/exception`` (bool): If set to ``True``, an exception will be
        raised whenever logging the message at ``WARNING`` level

      - ``warning/debug`` (bool): If set to ``True``, whenever logging the
        message at ``WARNING`` level the debugger will be started and execution
        paused

    - ``error``: Configuration for logging at ``ERROR`` level.

      - ``error/exception`` (bool): If set to ``True``, an exception will be
        raised whenever logging the message at ``ERROR`` level

      - ``error/debug`` (bool): If set to ``True``, whenever logging the
        message at ``ERROR`` level the debugger will be started and execution
        paused

    - ``print_traceback`` (bool): If set to ``True``, the traceback will be
      printed along with the log message.

    Sets the verbosity level for the ``core`` logger at ``INFO`` level:

    >>> bind('logger/core/level', INFO)

    Configures the ``typing`` logger to throw exception on warnings:

    >>> bind('logger/typing/warning/exception', True)

    '''
    dflt_action = {'debug': False, 'exception': False}
    dflt_severity = {
        'print_traceback': True,
        'warning': copy.deepcopy(dflt_action),
        'error': copy.deepcopy(dflt_action),
        'level': WARNING
    }

    def __init__(self, name, verbosity=INFO):
        self.name = name
        self.verbosity = verbosity

        self.set_default_logger()

        bind_val = copy.deepcopy(self.dflt_severity)
        bind_val['level'] = verbosity
        reg_name = f'logger/{name}'
        safe_bind(reg_name, bind_val)
        set_cb(f'{reg_name}/level', partial(set_log_level, name))

        self.logger = logging.getLogger(name)

        self.wrap = LogWrap(self.logger)
        self.logger.warning = self.wrap.warning
        self.logger.error = self.wrap.error

    def get_format(self):
        return logging.Formatter(
            '%(name)s [%(levelname)s]: %(message)s %(err_file)s %(stack_file)s'
        )

    def get_filter(self):
        return LogFmtFilter()

    def get_logger_handler(self):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.verbosity)
        ch.setFormatter(self.get_format())
        ch.addFilter(self.get_filter())
        return ch

    def set_default_logger(self):
        logger = logging.getLogger(self.name)
        logger.handlers.clear()
        logger.setLevel(self.verbosity)
        ch = self.get_logger_handler()
        logger.addHandler(ch)


class LogPlugin(PluginBase):
    @classmethod
    def bind(cls):
        tf = tempfile.NamedTemporaryFile(delete=False)
        safe_bind('logger/stack_traceback_fn', tf.name)

        CustomLog('core', WARNING)
        CustomLog('typing', WARNING)
        CustomLog('util', WARNING)
        CustomLog('gear', WARNING)
        CustomLog('conf', WARNING)


def core_log():
    return logging.getLogger('core')


def typing_log():
    return logging.getLogger('typing')


def util_log():
    return logging.getLogger('util')


def gear_log():
    return logging.getLogger('gear')


def conf_log():
    return logging.getLogger('conf')
