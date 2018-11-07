"""This module implements various logging facilities for the PyGears framework.
It is a wrapper around standard Python `logging
<https://docs.python.org/library/logging.html>`__ but provides some additional
features like:

- automatic exception raising when logging at any level
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
import sys
import tempfile

from functools import partial
from logging import INFO, WARNING, ERROR, DEBUG, CRITICAL, NOTSET

from .registry import PluginBase, safe_bind, registry, set_cb
from .trace import enum_stacktrace

HOOKABLE_LOG_METHODS = [
    'critical', 'exception', 'error', 'warning', 'info', 'debug'
]


class LogException(Exception):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


def set_log_level(name, level):
    log = logging.getLogger(name)
    if log.level != level:
        log.setLevel(level)
        for h in log.handlers:
            h.setLevel(level)
    conf_log().info(f'Setting log level {name}, {level}')


def stack_trace(name, verbosity, message):
    stack_traceback_fn = registry('logger/stack_traceback_fn')
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


def log_parent(cls, severity):
    def wrapper(self, msg, *args, **kwargs):
        '''Wrapper around logger methods from HOOKABLE_LOG_METHODS
        for calling hooks'''
        getattr(super(CustomLogger, self), severity)(msg, *args, **kwargs)

        if severity in ['error', 'warning']:
            stack_trace(self.name, severity, msg)
        getattr(self, f'{severity}_hook')(logger_name=self.name, message=msg)

    return wrapper


def log_action_exception(name, message):
    raise LogException(message, name)


def log_action_debug():
    import pdb
    pdb.set_trace()


def custom_action(logger_name, message, severity):
    log_cfg = registry('logger')[logger_name]
    if severity in log_cfg:
        if log_cfg[severity] == 'exception':
            log_action_exception(logger_name, message)
        elif log_cfg[severity] == 'debug':
            log_action_debug()
        else:
            # custom function in registry
            log_cfg[severity](message)


def log_hook(cls, severity):
    def wrapper(self, logger_name, message):
        '''Custom <severity>_hook methods for HOOKABLE_LOG_METHODS.'''
        custom_action(logger_name, message, severity)

    return wrapper


def hookable_methods_gen(cls):
    for severity in HOOKABLE_LOG_METHODS:
        setattr(cls, severity, log_parent(cls, severity))
        setattr(cls, f'{severity}_hook', log_hook(cls, severity))
    return cls


@hookable_methods_gen
class CustomLogger(logging.Logger):
    '''Inherits from Logger and adds hook methods to HOOKABLE_LOG_METHODS'''

    def __init__(self, name):
        super(CustomLogger, self).__init__(name)


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
    - ``print_traceback`` (bool): If set to ``True``, the traceback will be
      printed along with the log message.

    - optional level name with desired action. Custom actions can be set for
      any verbosity level by passing the function or any already supported
      action to the appropriate registry subtree. Supported actions are:

      - ``exception``: if set, an exception will be raised whenever logging the
        message at the desired level
      - ``debug``: if set, the debugger will be started and execution paused

    Sets the verbosity level for the ``core`` logger at ``INFO`` level:

    >>> bind('logger/core/level', INFO)

    Configures the ``typing`` logger to throw exception on warnings:

    >>> bind('logger/typing/warning', 'exception')

    Configures the ``conf`` logger to use custom function on errors:

    >>> bind('logger/conf/errors', custom_func)
    '''
    dflt_settings = {'print_traceback': True, 'level': WARNING}

    def __init__(self, name, verbosity=INFO):
        self.name = name
        self.verbosity = verbosity

        self.set_default_logger()

        bind_val = copy.deepcopy(self.dflt_settings)
        bind_val['level'] = verbosity
        reg_name = f'logger/{name}'
        safe_bind(reg_name, bind_val)
        set_cb(f'{reg_name}/level', partial(set_log_level, name))

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

        logging.setLoggerClass(CustomLogger)

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
