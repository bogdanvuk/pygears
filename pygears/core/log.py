import copy
import logging
import sys
import traceback
import tempfile
from string import Template

from pygears import bind, registry
from pygears.registry import PluginBase

registry_log_name = Template('${name}Log')


class LogWrap:
    def __init__(self, logger):
        self.logger = logger
        self.name = logger.name

    def severity_action(self, severity, message):
        log_cfg = registry(registry_log_name.substitute(name=self.name))
        if log_cfg[severity]['exception']:
            raise Exception(message)
        elif log_cfg[severity]['debug']:
            import pdb
            pdb.set_trace()

    def stack_trace(self):
        stack_traceback_fn = registry('StackTracebackFn')
        with open(stack_traceback_fn, 'a') as f:
            delim = '-' * 50 + '\n'
            f.write(delim)
            traceback.print_stack(file=f)
            f.write(delim)

    def warning(self, message, *args, **kws):
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger._log(logging.WARNING, message, args, **kws)

            self.stack_trace()
            self.severity_action('warning', message)

    def error(self, message, *args, **kws):
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger._log(logging.ERROR, message, args, **kws)
            self.stack_trace()
            self.severity_action('error', message)


class LogFmtFilter(logging.Filter):
    def filter(self, record):
        record.stack_file = ''

        if record.levelno > 20:  # > INFO
            stack_traceback_fn = registry('StackTracebackFn')
            stack_num = sum(1 for line in open(stack_traceback_fn))
            record.stack_file = f'\n\t File "{stack_traceback_fn}", line {stack_num}, for stacktrace'

        return True


class CustomLog:
    dflt_action = {'debug': False, 'exception': False}
    dflt_severity = {
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

    def get_default_logger_handler(self):
        fmt = logging.Formatter(
            '%(name)s log [%(levelname)s]: %(message)s \n\t File "%(pathname)s", line %(lineno)d, in %(funcName)s %(stack_file)s'
        )
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.verbosity)
        ch.setFormatter(fmt)
        ch.addFilter(LogFmtFilter())
        return ch

    def set_default_logger(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(self.verbosity)
        ch = self.get_default_logger_handler()
        logger.addHandler(ch)


class LogPlugin(PluginBase):
    @classmethod
    def bind(cls):
        tf = tempfile.NamedTemporaryFile(delete=False)
        stack_traceback_fn = tf.name
        open(stack_traceback_fn, 'w').close()  # clear previous
        bind('StackTracebackFn', stack_traceback_fn)

        CustomLog('core')
        CustomLog('typing')


def core_log():
    return logging.getLogger('core')


def typing_log():
    return logging.getLogger('typing')
