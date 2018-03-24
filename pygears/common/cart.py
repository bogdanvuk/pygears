from pygears.core.gear import Gear, gear, hier
from pygears import Queue, Tuple


def lvl_if_queue(t):
    if not issubclass(t, Queue):
        return 0
    else:
        return t.lvl


def calc_cart_type(args):
    arg_queue_lvl = [lvl_if_queue(a.dtype) for a in args]

    base_type = Tuple[tuple(t.dtype if lvl == 0 else t.dtype[0]
                            for t, lvl in zip(args, arg_queue_lvl))]

    # If there are no Queues, i.e. sum(arg_queue_lvl) == 0, the type below
    # will resolve to just base_type
    return Queue[base_type, sum(arg_queue_lvl)]


class Cart(Gear):
    def infer_params_and_ftypes(self):
        ftypes, params = super().infer_params_and_ftypes()
        ftypes[-1] = calc_cart_type(self.args)

        return ftypes, params


@hier
def cart_vararg(*din):
    ret = cart(din[0], din[1])
    for d in din[2:]:
        ret = cart(ret, d)

    return ret | calc_cart_type(din)


@gear(gear_cls=Cart, alternatives=[cart_vararg], enablement='len({din}) == 2')
def cart(*din):
    pass
