import random
from functools import partial

from nose import with_setup

from pygears import clear
from pygears.cookbook.chunk_concat import chunk_concat
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Uint
from utils import skip_ifndef

t_din = Queue[Uint[16]]
t_cfg = Uint[16]


def get_stim(din_num=4):
    cfg_seq = []
    din_seq = {k: [] for k in range(din_num)}
    cfg_num = random.randint(2, 10)
    for i in range(cfg_num):
        prev = cfg_seq[-1] if len(cfg_seq) else din_num
        active = random.randint(1, prev)
        cnt = random.randint(1, 10)
        cfg_seq.extend([active] * cnt)
        for d in range(active):
            din_seq[d].append(list(range(cnt)))

    din = [drv(t=t_din, seq=din_seq[i]) for i in range(din_num)]
    return [drv(t=t_cfg, seq=cfg_seq), *din]


# @with_setup(clear)
# def test_pygears_sim():
#     din_num = 4

#     directed(
#         drv(t=t_cfg, seq=[din_num] * 8),
#         *[drv(t=t_din, seq=[list(range(5)), list(range(3))])] * din_num,
#         f=chunk_concat(cnt_type=1, chunk_size=1, pad=0),
#         ref=[[[i] * din_num for i in range(5)],
#              [[i] * din_num for i in range(3)]])

#     sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')

    stim = get_stim(4)
    verif(
        *stim,
        f=chunk_concat(sim_cls=partial(SimSocket, run=True), cnt_type=1),
        ref=chunk_concat(name='ref_model', cnt_type=1))

    sim()


@with_setup(clear)
def test_verilator_cosim():
    skip_ifndef('VERILATOR_ROOT')

    stim = get_stim(4)
    verif(
        *stim,
        f=chunk_concat(sim_cls=SimVerilated, cnt_type=1),
        ref=chunk_concat(name='ref_model', cnt_type=1))

    sim()
