# ===========================================================================
# Logger usage:
#
# To add new logger:
#  - create CustomLog instance
#  - create <name>_log() wrapper function
#
# To overwrite default behaviour:
#  - change appropriate values in registry(<name>Log)[verbosity][action]
#    - verbosity: error or warning
#    - action: exception or debug
#    For example: registry('coreLog')['error']['exception'] = False
#  - to print traceback on fail: registry(<name>Log)['print_traceback'] = True
#
# To change verbosity of displayed messages set the desired level:
#   For example: core_log().level = logging.ERROR
#
# ===========================================================================

import copy
import logging
import sys
import tempfile
from string import Template

from pygears import bind, registry
from pygears.registry import PluginBase

from .err import enum_stacktrace

registry_log_name = Template('${name}Log')


class LogException(Exception):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


class LogWrap:
    def __init__(self, logger):
        self.logger = logger
        self.name = logger.name

    def severity_action(self, severity, message):
        log_cfg = registry(registry_log_name.substitute(name=self.name))
        if log_cfg[severity]['exception']:
            raise LogException(message, self.name)
        elif log_cfg[severity]['debug']:
            import pdb
            pdb.set_trace()

    def stack_trace(self, verbosity, message):
        stack_traceback_fn = registry('StackTracebackFn')
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
        if self.logger.isEnabledFor(logging.WARNING):
            severity = 'warning'
            self.logger._log(logging.WARNING, message, args, **kws)
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

        if record.levelno > 20:  # > INFO
            stack_traceback_fn = registry('StackTracebackFn')
            stack_num = sum(1 for line in open(stack_traceback_fn))
            record.stack_file = f'\n\t File "{stack_traceback_fn}", line {stack_num}, for stacktrace'
            record.err_file = f'\n\t File "{record.pathname}", line {record.lineno}, in {record.funcName}'

        return True


class CustomLog:
    dflt_action = {'debug': False, 'exception': False}
    dflt_severity = {
        'print_traceback': True,
        'warning': copy.deepcopy(dflt_action),
        'error': copy.deepcopy(dflt_action)
    }

    def __init__(self, name, verbosity=logging.INFO):
        self.name = name
        self.verbosity = verbosity

        self.set_default_logger()
        bind(
            registry_log_name.substitute(name=name),
            copy.deepcopy(self.dflt_severity))

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
        logger.setLevel(self.verbosity)
        ch = self.get_logger_handler()
        logger.addHandler(ch)


class LogPlugin(PluginBase):
    @classmethod
    def bind(cls):
        tf = tempfile.NamedTemporaryFile(delete=False)
        bind('StackTracebackFn', tf.name)

        CustomLog('core', logging.WARNING)
        CustomLog('typing', logging.WARNING)
        CustomLog('util', logging.WARNING)
        CustomLog('gear', logging.WARNING)


def core_log():
    return logging.getLogger('core')


def typing_log():
    return logging.getLogger('typing')


def util_log():
    return logging.getLogger('util')


def gear_log():
    return logging.getLogger('gear')
