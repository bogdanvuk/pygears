from pygears import gear
from pygears.lib import directed, drv
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


# async def qrange(din):
#     cnt = 0
#     while (cnt < din):
#         yield cnt
#         cnt += 1

from pygears.typing import Integer


# @gear(hdl={'compile': True})
# async def qrange(din: Integer) -> Queue[b'din']:
#     cnt: din.dtype = 0
#     cur_cnt: din.dtype

#     async with din as d:
#         while (cnt < d):
#             cur_cnt = cnt
#             cnt += 1
#             yield cur_cnt, cnt == d

# @gear(hdl={'compile': True})
# async def qrange(cfg: Tuple[Integer, Integer]) -> Queue[b'cfg[0]']:
#     cnt: cfg.dtype[0] = None
#     cur_cnt: cfg.dtype[0]

#     async with cfg as c:
#         cnt_next = c[0]
#         inited = False
#         while (cnt < c[1]):
#             assign cnt = (cnt if inited else c[0])

#             cur_cnt = cnt
#             inited = True
#             cnt_next = cnt + 1
#             yield cur_cnt, cnt_next == c[1]
#             cnt = cnt_next

# FORWARDING!!!!
@gear(hdl={'compile': True})
async def qrange(cfg: Tuple[Integer, Integer]) -> Queue[b'cfg[0]']:
    cnt: cfg.dtype[0] = None
    cur_cnt: cfg.dtype[0]

    async with cfg as c:
        cnt = c[0]
        while (cnt < c[1]):
            # cnt = init ? c[0] : cnt
            cur_cnt = cnt
            cnt += 1
            # cnt = (init ? c[0] : cnt) + 1
            yield cur_cnt, cnt == c[1]


@gear(hdl={'compile': True})
async def inv(din: Uint, *, init=1) -> b'din':
    async with din as data:
        async for d, last in qrange(data):
            print(d, last)
            yield d


from pygears import config
from pygears.lib import drv, shred, directed

# drv(t=Uint[4], seq=[4]) | inv | shred
# from pygears.sim import sim, cosim
# config['debug/trace'] = ['*']
# cosim('/inv', 'verilator')
# sim('/tools/home/tmp/inv')

directed(drv(t=Tuple[Uint[4], Uint[4]], seq=[(4, 8)]), f=qrange, ref=[[0, 1, 2, 3]])
from pygears.sim import sim, cosim
config['debug/trace'] = ['*']
cosim('/qrange', 'verilator')
sim('/tools/home/tmp/qrange')

# from pygears.lib.group import group_other
# from pygears import Intf, find
# res = group_other(Intf(Uint[8]), Intf(Uint[4]))
# g = find('/group_other')

# from pygears.hdl.sv.svcompile2 import compile_gear_body
# res = compile_gear_body(find('/inv'))
# print(res)
