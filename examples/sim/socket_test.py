import random

from pygears import GearDone, gear
from pygears.cookbook.replicate import replicate
from pygears.cookbook.trr import trr
from pygears.cookbook.verif import verif
from pygears.sim import clk, sim
from pygears.sim.extens.svrand import (SVRandSocket, create_type_cons,
                                       get_rand_data)
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.utils import SimDelay
from pygears.typing import TLM, Queue, Tuple, Uint

t_din = Tuple[Uint[16], Uint[16]]
outdir = '/tools/home/tmp1'
cons = []
cons.append(
    create_type_cons(
        t_din,
        'din',
        cons=['din.f0 < 10', 'din.f0 > 2', 'din.f1 > 2', 'din.f1 < 10']))


@gear
async def get_random_data(*, t) -> TLM['t']:
    # soc = SVRandSocket(cons)
    for i in range(10):
        data = get_rand_data('din')
        print(f'Got data: {data}')

        dly = random.randint(5, 10)
        for i in range(dly):
            await clk()

        yield data

    # soc.finish()
    raise GearDone


def main():
    verif(
        # seqr(t=t_din, seq=[(1, 2), (3, 4)]),
        get_random_data(t=t_din),
        f=replicate(sim_cls=SimSocket),
        ref=replicate)

    sim(outdir=outdir, extens=[SVRandSocket], constraints=cons)


t_trr = Queue[Uint[16]]
trr_cons = []
trr_cons.append(
    create_type_cons(
        Uint[16], 'din0_data', cons=['din0_data dist {5:=50, 10:=50}']))
trr_cons.append(
    create_type_cons(
        Uint[16], 'din1_data', cons=['din1_data dist {0:=50, 1:=50}']))
trr_cons.append(
    create_type_cons(
        Uint[16], 'din2_data', cons=[]))
trr_cons.append(
    create_type_cons(
        t_trr.eot,
        'din_eot',
        cons=['num_trans[0][0] == 20'],
        cls='qenvelope',
        cls_params=[t_trr.lvl]))
# trr_cons.append(
#     create_type_cons(t_trr, 'din1', cons=['din1.data dist {0:=50, 1:=50}']))
# trr_cons.append(
#     create_type_cons(t_trr, 'din2', cons=['din2.data dist {0:=10, 1:=90}']))


def get_data(i):
    x = 0
    while x == 0:
        data = get_rand_data(f'din{i}')
        yield data[0]
        x = data[1]


def get_data_eot(i):
    eot = 0
    while eot == 0:
        eot = get_rand_data('din_eot')
        data = get_rand_data(f'din{i}_data')
        yield data


@gear
async def vir_seqr(*, t=t_trr) -> (TLM['t'], ) * 3:
    for x in range(10):
        yield (get_data_eot(0), None, None)
        yield (None, get_data_eot(1), None)
        yield (None, None, get_data_eot(2))
    raise GearDone


def trr_main():
    sequencers = vir_seqr()
    delays = [SimDelay(1, 10)] * 3
    delays.append(SimDelay(0, 0))  # ready always high
    verif(
        *sequencers,
        f=trr(sim_cls=SimSocket),
        ref=trr(name='ref_model'),
        delays=delays)

    sim(outdir=outdir, extens=[SVRandSocket], constraints=trr_cons)


def py_trr_main():
    sequencers = vir_seqr()
    delays = [SimDelay(1, 10)] * 3
    delays.append(SimDelay(0, 0))  # ready always high
    verif(*sequencers, f=trr, ref=trr(name='ref_model'), delays=delays)

    sim(outdir=outdir, extens=[SVRandSocket], constraints=trr_cons)


if __name__ == '__main__':
    trr_main()
