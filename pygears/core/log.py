import copy
import logging
import sys
from string import Template

from pygears import bind, registry
from pygears.registry import PluginBase

registry_log_name = Template('${name}Log')


def core_log():
    return logging.getLogger('core')


def typing_log():
    return logging.getLogger('typing')


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

    def warning(self, message, *args, **kws):
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger._log(logging.WARNING, message, args, **kws)
            self.severity_action('warning', message)

    def error(self, message, *args, **kws):
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger._log(logging.ERROR, message, args, **kws)
            self.severity_action('error', message)


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
            '%(name)s %(module)s [%(levelname)s]: %(message)s')
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.verbosity)
        ch.setFormatter(fmt)
        return ch

    def set_default_logger(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(self.verbosity)
        ch = self.get_default_logger_handler()
        logger.addHandler(ch)


class LogPlugin(PluginBase):
    @classmethod
    def bind(cls):
        CustomLog('core')
        CustomLog('typing')
