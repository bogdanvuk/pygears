from pygears import gear
from pygears.lib import directed, drv, delay_rng, collect
from pygears.sim import sim
from pygears.typing import Bool, Queue, Tuple, Uint
from pygears.util.utils import gather


def test_inline_if(tmpdir, cosim_cls):
    @gear(hdl={'compile': True})
    async def inv(din: Bool) -> Bool:
        async with din as data:
            yield 0 if data else 1

    directed(drv(t=Bool, seq=[1, 0]), f=inv(sim_cls=cosim_cls), ref=[0, 1])

    sim(tmpdir)


# # async def qrange(din):
# #     cnt = 0
# #     while (cnt < din):
# #         yield cnt
# #         cnt += 1

# from pygears.typing import Integer


# # @gear(hdl={'compile': True})
# # async def qrange(din: Integer) -> Queue[b'din']:
# #     cnt: din.dtype = 0
# #     cur_cnt: din.dtype

# #     async with din as d:
# #         while (cnt < d):
# #             cur_cnt = cnt
# #             cnt += 1
# #             yield cur_cnt, cnt == d


# # FORWARDING!!!!
# @gear(hdl={'compile': True})
# async def qrange(cfg: Tuple[Integer, Integer]) -> Queue[b'cfg[0]']:
#     cnt: cfg.dtype[0] = None
#     cur_cnt: cfg.dtype[0]

#     async with cfg as c:
#         cnt = c[0]

#         # cycle_en = c[0] < c[1]
#         # cnt = cycle ? c[0] : cnt
#         # opt_in_cond = ((cycle ? c[0] : cnt) < c[1])
#         while (cnt < c[1]):
#             cur_cnt = cnt
#             cnt += 1
#             # cnt = (cycle ? c[0] : cnt) + 1
#             yield cur_cnt, cnt == c[1]

#         # cnt = opt_in_cond ? ((cycle ? c[0] : cnt) + 1) : (c[0])
#         # if cnt < c[1]: break


# @gear(hdl={'compile': True})
# async def inv(din: Uint, *, init=1) -> b'din':
#     async with din as data:
#         async for d, last in qrange(data):
#             print(d, last)
#             yield d


# from pygears import config
# from pygears.lib import drv, shred, directed

# # drv(t=Uint[4], seq=[4]) | inv | shred
# # from pygears.sim import sim, cosim
# # config['debug/trace'] = ['*']
# # cosim('/inv', 'verilator')
# # sim('/tools/home/tmp/inv')

# # directed(drv(t=Tuple[Uint[4], Uint[4]], seq=[(4, 8)]), f=qrange, ref=[list(range(4, 8))])

# # directed(drv(t=Uint[4], seq=[4]) | delay_rng(1, 5),
# #          f=qrange,
# #          ref=[list(range(4))],
# #          delays=[delay_rng(1, 5)])

# res = []

# # drv(t=Uint[4], seq=[0]) | delay_rng(1, 5) | qrange | collect(result=res)
# drv(t=Tuple[Uint[4], Uint[4]], seq=[(4, 8)]) | delay_rng(1, 5) | qrange | collect(result=res)

# from pygears.sim import sim, cosim
# config['debug/trace'] = ['*']
# cosim('/qrange', 'verilator')
# sim('/tools/home/tmp/qrange')
# print(res)

# # from pygears.lib.group import group_other
# # from pygears import Intf, find
# # res = group_other(Intf(Uint[8]), Intf(Uint[4]))
# # g = find('/group_other')

# # from pygears.hdl.sv.svcompile2 import compile_gear_body
# # res = compile_gear_body(find('/inv'))
# # print(res)
