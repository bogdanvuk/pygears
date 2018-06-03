from nose import with_setup
from utils import sim_check
from pygears import clear

from pygears import gear
from pygears.sim import verif
from pygears.sim.modules.dtype_rnd_seq import dtype_rnd_seq
from pygears.sim.scv import create_type_cons
from pygears.typing import Queue, Uint, Tuple, TLM
from pygears.cookbook.rng import rng


@with_setup(clear)
@sim_check()
def test_cnt_svgen():
    t_cfg = Tuple[Uint[4], Uint[4], Uint[2]]
    params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)

    cons = create_type_cons(
        t_cfg,
        scale=Uint[4],
        cons=['scale > 0', 'f1 > f0', 'f1 - f0 == scale*f2'])

    @gear
    async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
                  cnt_one_more) -> TLM[Queue[Uint[4]]]:
        cfg = await din.get()
        din.task_done()

        cfg = list(cfg)
        cfg[1] += 1
        yield list(range(*cfg))

    return verif(
        dtype_rnd_seq(t=t_cfg, cons=cons), f=rng(**params), ref=ref(**params))
