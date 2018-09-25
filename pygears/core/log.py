from pygears.registry import PluginBase
from functools import partial
import sys
import logging


def core_log():
    return logging.getLogger('core')


def typing_log():
    return logging.getLogger('typing')


def warning_to_exception(message, name, *args, **kws):
    log = logging.getLogger(name)
    if log.isEnabledFor(logging.WARNING):
        log._log(logging.WARNING, message, args, **kws)
        raise Exception(message)


def get_default_logger_handler(verbosity):
    fmt = logging.Formatter('%(name)s %(module)s [%(levelname)s]: %(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(verbosity)
    ch.setFormatter(fmt)
    return ch


def set_default_logger(name, verbosity):
    logger = logging.getLogger(name)
    logger.setLevel(verbosity)
    ch = get_default_logger_handler(verbosity=verbosity)
    logger.addHandler(ch)


class LogPlugin(PluginBase):
    @classmethod
    def bind(cls):
        set_default_logger('core', logging.INFO)
        set_default_logger('typing', logging.INFO)

        # core_log().warning = partial(warning_to_exception, name='core')
        # typing_log().warning = partial(warning_to_exception, name='typing')
