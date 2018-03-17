from pygears.registry import registry, PluginBase
from enum import Enum
import sys


class ErrReportLevel(Enum):
    debug = 0
    user = 1


class ErrReportPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['ErrReportLevel'] = ErrReportLevel.user


def pygears_excepthook(exception_type,
                       exception,
                       traceback,
                       debug_hook=sys.excepthook):
    if registry("ErrReportLevel") == ErrReportLevel.debug:
        debug_hook(exception_type, exception, traceback)
    else:
        from traceback import extract_tb, format_list, walk_tb
        from traceback import format_exception_only
        # from pygears.util.print_hier import print_hier
        # from pygears import find
        import os

        # try:
        #     print_hier(find('/'))
        # except Exception as e:
        #     pass

        for s, t in zip(
                format_list(extract_tb(traceback)), walk_tb(traceback)):
            if not t[0].f_code.co_filename.startswith(
                    os.path.dirname(__file__)):
                print(s, end='')

        print(format_exception_only(exception_type, exception)[0])
