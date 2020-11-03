import logging


def debug(msg, *args, **kwds):
    return logging.getLogger('sim').debug(msg, *args, **kwds)


def info(msg, *args, **kwds):
    return logging.getLogger('sim').info(msg, *args, **kwds)


def warning(msg, *args, **kwds):
    return logging.getLogger('sim').warning(msg, *args, **kwds)


def error(msg, *args, **kwds):
    return logging.getLogger('sim').error(msg, *args, **kwds)


def critical(msg, *args, **kwds):
    return logging.getLogger('sim').critical(msg, *args, **kwds)


def log(level, msg, *args, **kwds):
    return logging.getLogger('sim').log(level, msg, *args, **kwds)


def exception(msg, *args, **kwds):
    return logging.getLogger('sim').exception(msg, *args, **kwds)
