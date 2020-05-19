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

import copy
import logging
import os
import sys
import tempfile
from functools import partial
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING

from .registry import Inject, PluginBase, inject, reg
from .trace_format import enum_stacktrace

HOOKABLE_LOG_METHODS = ['critical', 'error', 'warning', 'info', 'debug']


class LogException(Exception):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


def set_log_level(var, level, name):
    log = logging.getLogger(name)
    if log.level != level:
        log.setLevel(level)
        for h in log.handlers:
            h.setLevel(level)


def log_parent(cls, severity):
    def wrapper(self, msg, *args, **kwargs):
        '''Wrapper around logger methods from HOOKABLE_LOG_METHODS
        for calling hooks'''
        getattr(super(CustomLogger, self), severity)(msg, *args, **kwargs)
        getattr(self, f'{severity}_hook')(logger_name=self.name, message=msg)

    return wrapper


def log_action_exception(name, message):
    raise LogException(message, name)


def log_action_debug():
    import pdb
    pdb.set_trace()


@inject
def custom_action(logger_name, message, severity, log_cfgs=Inject('logger')):
    method = reg[f'logger/{logger_name}/{severity}']
    if method == 'exception':
        log_action_exception(logger_name, message)
    elif method == 'debug':
        log_action_debug()
    elif method == 'pass':
        pass
    elif callable(method):
        # custom function in registry
        method(message)


def log_hook(cls, severity):
    @inject
    def wrapper(self, logger_name, message, hooks=Inject('logger/hooks')):
        '''Custom <severity>_hook methods for HOOKABLE_LOG_METHODS.'''
        custom_action(logger_name, message, severity)
        for hook in hooks:
            hook(logger_name, severity, message)

    return wrapper


def hookable_methods_gen(cls):
    for severity in HOOKABLE_LOG_METHODS:
        setattr(cls, severity, log_parent(cls, severity))
        setattr(cls, f'{severity}_hook', log_hook(cls, severity))
    return cls


class LogFmtFilter(logging.Filter):
    @inject
    def __init__(self,
                 name='',
                 stack_traceback_fn=Inject('logger/stack_traceback_fn')):
        super(LogFmtFilter, self).__init__(name)
        self.stack_traceback_fn = stack_traceback_fn

    def filter(self, record):
        record.stack_file = ''
        record.err_file = ''

        if record.levelno > INFO:
            if os.path.exists(self.stack_traceback_fn):
                with open(self.stack_traceback_fn) as f:
                    stack_num = sum(1 for _ in f)
            else:
                stack_num = 0

            # TODO: improve error reporting in this way
            record.stack_file = f'\n  File "{self.stack_traceback_fn}", line {stack_num}, for stacktrace'
            *_, last_frame = enum_stacktrace()
            record.err_file = f'\n{last_frame}' [:-1]

        return True


@hookable_methods_gen
class CustomLogger(logging.Logger):
    '''Inherits from Logger and adds hook methods to HOOKABLE_LOG_METHODS'''
    def __init__(self, name, level=INFO):
        super(CustomLogger, self).__init__(name, level)

    def get_format(self):
        return logging.Formatter(
            '%(name)s [%(levelname)s]: %(message)s %(err_file)s %(stack_file)s'
        )

    def get_filter(self):
        return LogFmtFilter()

    def get_logger_handler(self, handler=None):
        if handler is None:
            handler = logging.StreamHandler(sys.stdout)

        handler.setLevel(self.level)
        handler.setFormatter(self.get_format())

        filt = self.get_filter()
        if filt is not None:
            handler.addFilter(filt)

        return handler


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


def register_custom_log(name, level=INFO, cls=CustomLogger):
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
      - ``pass``: if set, the message will be printed and no further action
        taken; this is usefull for clearing prevously set values

    Sets the verbosity level for the ``core`` logger at ``INFO`` level:

    >>> reg['logger/core/level'] = INFO

    Configures the ``typing`` logger to throw exception on warnings:

    >>> reg['logger/typing/warning'] = 'exception'

    Configures the ``conf`` logger to use custom function on errors:

    >>> reg['logger/conf/errors'] = custom_func
    '''
    log_cls = logging.getLoggerClass()
    logging.setLoggerClass(cls)

    reg_name = f'logger/{name}'

    for m in HOOKABLE_LOG_METHODS:
        reg.confdef(f'{reg_name}/{m}', default='pass')

    reg.confdef(f'{reg_name}/level',
                  default=level,
                  setter=partial(set_log_level, name=name))

    reg.confdef(f'{reg_name}/print_traceback', default=True)

    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level)
    logger.addHandler(logger.get_logger_handler())

    logging.setLoggerClass(log_cls)


class LogPlugin(PluginBase):
    @classmethod
    def bind(cls):
        tf = tempfile.NamedTemporaryFile(delete=False)
        reg['logger/stack_traceback_fn'] = tf.name
        reg['logger/hooks'] = []

        register_custom_log('core', WARNING)
        register_custom_log('typing', WARNING)
        register_custom_log('util', WARNING)
        register_custom_log('gear', WARNING)
        register_custom_log('conf', WARNING)
