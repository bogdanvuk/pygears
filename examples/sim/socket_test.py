from pygears.cookbook.replicate import replicate
from pygears.cookbook.verif import verif
from pygears.typing import TLM
from pygears.sim.modules.socket import SimSocket
from pygears.sim import sim
from pygears.typing import Tuple, Uint
from pygears.sim import clk
import random
from pygears import GearDone, gear
from pygears.sim.modules.svrand import (create_type_cons,
                                        get_svrand_constraint, SVRandSocket)

t_din = Tuple[Uint[16], Uint[16]]
outdir = '/tools/home/tmp1/cons'
cons = []
cons.append(
    create_type_cons(
        t_din,
        'din',
        cons=['din.f0 < 10', 'din.f0 > 2', 'din.f1 > 2', 'din.f1 < 10']))


@gear
async def get_random_data(*, t) -> TLM['t']:
    soc = SVRandSocket(cons)
    for i in range(10):
        data = soc.get_rand('din')

        dly = random.randint(5, 10)
        for i in range(dly):
            await clk()

        yield data

    soc.finish()
    raise GearDone


def main():
    get_svrand_constraint(outdir, cons, start_cadence=False)
    verif(
        get_random_data(t=t_din),
        f=replicate(sim_cls=SimSocket),
        ref=replicate,
        dly_out=True)

    sim(outdir='/tools/home/tmp1')


if __name__ == '__main__':
    main()
