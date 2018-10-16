import sys
from functools import partial
from traceback import format_exception_only

from .pdb_patch import patch_pdb, unpatch_pdb
from .registry import PluginBase, RegistryHook, registry
from .trace import ErrReportLevel, enum_traceback


class ErrReport(RegistryHook):
    def _set_level(self, val):
        if val == ErrReportLevel.user:
            patch_pdb()
        else:
            unpatch_pdb()


class ErrReportPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['err'] = ErrReport(level=ErrReportLevel.debug)
        cls.registry['err']['hooks'] = []


def register_exit_hook(hook, *args, **kwds):
    registry('err/hooks').append(partial(hook, *args, **kwds))


def pygears_excepthook(exception_type,
                       exception,
                       tr,
                       debug_hook=sys.excepthook):

    for hook in registry('err/hooks'):
        try:
            hook()
        except:
            pass

    if registry('err/level') == ErrReportLevel.debug:
        debug_hook(exception_type, exception, tr)
    else:
        from pygears.util.print_hier import print_hier
        from pygears import find

        try:
            print_hier(find('/'))
        except Exception as e:
            pass

        # print traceback for LogException only if appropriate
        # 'print_traceback' in registry is set
        from pygears.conf.log import LogException
        print_traceback = (exception_type is not LogException)
        if not print_traceback:
            print_traceback = registry(
                f'logger/{exception.name}/print_traceback')
        if print_traceback:
            for s in enum_traceback(tr):
                print(s, end='')

        print(format_exception_only(exception_type, exception)[0])
