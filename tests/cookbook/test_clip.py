import random
from functools import partial

from pygears.cookbook.clip import clip
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import prepare_result_dir, skip_ifndef

t_din = Queue[Uint[16]]
t_cfg = Uint[16]


def test_directed(tmpdir, sim_cls):
    directed(
        drv(t=t_din, seq=[list(range(9)), list(range(5))]),
        drv(t=t_cfg, seq=[2, 3]),
        f=clip(sim_cls=sim_cls),
        ref=[[0, 1],
             list(range(2, 9)),
             list(range(3)),
             list(range(3, 5))])

    sim(outdir=tmpdir)


def test_random(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')

    cfg_seq = []
    din_seq = []
    cfg_num = random.randint(2, 10)
    for i in range(cfg_num):
        cfg_seq.append(random.randint(1, 10))
        din_seq.append(list(range(random.randint(1, 10))))

    verif(
        drv(t=t_din, seq=din_seq),
        drv(t=t_cfg, seq=cfg_seq),
        f=clip(sim_cls=sim_cls),
        ref=clip(name='ref_model'))

    sim(outdir=tmpdir)


def test_random_constrained(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cnt = 5
    cons = []
    cons.append(create_constraint(t_din, 'din', eot_cons=['data_size == 20']))
    cons.append(create_constraint(t_cfg, 'cfg', cons=['cfg < 20', 'cfg > 0']))

    stim = []
    stim.append(drv(t=t_din, seq=rand_seq('din', cnt)))
    stim.append(drv(t=t_cfg, seq=rand_seq('cfg', cnt)))

    verif(
        *stim,
        f=clip(sim_cls=partial(SimSocket, run=True)),
        ref=clip(name='ref_model'))

    sim(outdir=prepare_result_dir(), extens=[partial(SVRandSocket, cons=cons)])
