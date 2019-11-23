from pygears import gear, module
from pygears.sim.extens.randomization import randomize, rand_seq
from .verif import drv


@gear
def drvrnd(*, t, cnt=None, cons=None, params=None):
    return drv(
        t=t, seq=randomize(t, module().basename, cnt=cnt, cons=cons, params=params))
