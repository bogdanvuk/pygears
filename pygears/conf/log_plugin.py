from .registry import registry, RegistryHook
from . import log_pm, log_hookimpl


class LogException(Exception):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


def log_action_exception(name, message):
    raise LogException(message, name)


def log_action_debug():
    import pdb
    pdb.set_trace()


class LoggerRegistryHook(RegistryHook):
    def __init__(self, name):
        self.name = name

    def _set_error(self, val):
        log_pm.register(LoggerPlugin(name=self.name))

    def _set_warning(self, val):
        log_pm.register(LoggerPlugin(name=self.name))


class LoggerPlugin(object):
    def __init__(self, name):
        self.name = name

    def custom_action(self, msg, severity):
        log_cfg = registry('logger')[self.name]
        if severity in log_cfg:
            if log_cfg[severity] == 'exception':
                log_action_exception(self.name, msg)
            elif log_cfg[severity] == 'debug':
                log_action_debug()
            else:
                # custom function in registry
                log_cfg[severity](self.name, msg)

    @log_hookimpl
    def warning(self, msg):
        self.custom_action(msg, self.warning.__name__)

    @log_hookimpl
    def error(self, msg):
        self.custom_action(msg, self.error.__name__)
