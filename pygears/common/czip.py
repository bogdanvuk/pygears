from pygears.core.gear import Gear, gear
# from pygears.core.module_def import ModuleDefinition
# from pygears.typing.tuple import Tuple
# import pygears.typing.queue
# from pygears.typing.base import param_subs
from pygears import Queue, Tuple


def lvl_if_queue(t):
    if not issubclass(t, Queue):
        return 0
    else:
        return t.lvl


class CZip(Gear):
    def infer_params_and_ftypes(self):
        ftypes, params = super().infer_params_and_ftypes()

        arg_queue_lvl = [lvl_if_queue(a.dtype) for a in self.args]

        base_type = Tuple[tuple(t.dtype if lvl == 0 else t.dtype[0]
                                for t, lvl in zip(self.args, arg_queue_lvl))]
        ftypes[-1] = Queue[base_type, max(arg_queue_lvl)]

        return ftypes, params


@gear(gear_cls=CZip)
def czip(*din: '{{w_data{0}}}'):
    pass
