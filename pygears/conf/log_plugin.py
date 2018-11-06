from .registry import registry, RegistryHook
from . import log_pm, log_hookimpl

HOOKABLE_LOG_METHODS = [
    'critical', 'exception', 'error', 'warning', 'info', 'debug'
]


class LogException(Exception):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


def log_action_exception(name, message):
    raise LogException(message, name)


def log_action_debug():
    import pdb
    pdb.set_trace()


def log_pm_register(cls, name):
    def wrapper(self, val):
        '''Register hook if any value set in registy'''
        if val:
            log_pm.register(self.hook)
        else:
            log_pm.unregister(self.hook)

    return wrapper


def register_methods_gen(cls):
    for name in HOOKABLE_LOG_METHODS:
        setattr(cls, f'_set_{name}', log_pm_register(cls, name))
    return cls


@register_methods_gen
class LoggerRegistryHook(RegistryHook):
    '''Auto register/unregister hooks based on registry values
    contains _set_<verbosity> method for every HOOKABLE_LOG_METHODS
    '''

    def __init__(self, name):
        self.name = name
        self.hook = LoggerPlugin(name=self.name)


def log_plugin(cls, severity):
    @log_hookimpl
    def wrapper(self, msg, name):
        '''Perform custom action only if msg sent from appropriate logger'''
        if self.name == name:
            self.custom_action(msg, severity)

    return wrapper


def plugin_methods_gen(cls):
    for severity in HOOKABLE_LOG_METHODS:
        setattr(cls, f'{severity}_hook', log_plugin(cls, severity))
    return cls


@plugin_methods_gen
class LoggerPlugin(object):
    '''Hook impl. methods for every HOOKABLE_LOG_METHODS'''

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
