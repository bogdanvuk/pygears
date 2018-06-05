from nose import with_setup
from utils import sim_check, skip_sim_if_no_tools
from pygears import clear

from pygears import gear
from pygears.sim import verif
from pygears.sim.modules.dtype_rnd_seq import dtype_rnd_seq
from pygears.sim.modules.seqr import seqr
from pygears.sim.scv import create_type_cons
from pygears.typing import Queue, Uint, Tuple, TLM, Int
from pygears.cookbook.rng import rng

skip_sim_if_no_tools()


@with_setup(clear)
@sim_check()
def test_cnt_svgen_unsigned():
    t_cfg = Tuple[Uint[4], Uint[4], Uint[2]]
    params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)

    cons = create_type_cons(
        t_cfg,
        scale=Uint[4],
        cons=['scale > 0', 'f1 > f0', 'f1 - f0 == scale*f2'])

    @gear
    async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
                  cnt_one_more) -> TLM[Queue[t_cfg[0]]]:
        cfg = await din.get()
        din.task_done()

        cfg = list(cfg)
        cfg[1] += 1
        yield list(range(*cfg))

    return verif(
        seqr(t=t_cfg, seq=dtype_rnd_seq(t=t_cfg, cons=cons)),
        f=rng(**params),
        ref=ref(**params))


@with_setup(clear)
@sim_check()
def test_cnt_svgen_stop_only():
    t_cfg = Uint[8]
    params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)

    @gear
    async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
                  cnt_one_more) -> TLM[Queue[t_cfg]]:
        cfg = await din.get()
        din.task_done()

        yield list(range(cfg + 1))

    return verif(
        seqr(t=t_cfg, seq=dtype_rnd_seq(t=t_cfg)),
        f=rng(**params),
        ref=ref(**params))


# @with_setup(clear)
# @sim_check()
# def test_cnt_svgen_signed():
#     t_cfg = Tuple[Int[6], Int[6], Int[4]]
#     params = dict(cnt_steps=False, incr_steps=False, cnt_one_more=False)

#     cons = create_type_cons(
#         t_cfg,
#         scale=Int[2],
#         cons=['scale > 0', 'f0 > f1', 'f0 + scale*f2 == f1', 'f2 < 0'])

#     @gear
#     async def ref(din: TLM[t_cfg], *, cnt_steps, incr_steps,
#                   cnt_one_more) -> TLM[Queue[t_cfg[0]]]:
#         cfg = await din.get()
#         din.task_done()

#         cfg = list(cfg)
#         if cfg[1] > cfg[0]:
#             cfg[1] += 1
#         else:
#             cfg[1] -= 1

#         yield list(range(*cfg))

#     return verif(
#         dtype_rnd_seq(t=t_cfg, cons=cons), f=rng(**params), ref=ref(**params))

#     # return verif(
#     #     seqr(t=t_cfg, seq=[(-8, -22, -2)]), f=rng(**params), ref=ref(**params))
