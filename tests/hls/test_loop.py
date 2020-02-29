from pygears import gear, Intf
from pygears.typing import Bool, Uint, Queue
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed
from pygears.lib.rng import qrange


def test_for_loop(tmpdir):
    @gear(hdl={'compile': True})
    async def test(din: Uint) -> b'din':
        async with din as d:
            for i in range(d):
                yield i

    directed(drv(t=Uint[4], seq=[4, 2]),
             f=test,
             ref=list(range(4)) + list(range(2)))

    cosim('/test', 'verilator')
    sim(tmpdir)

test_for_loop('/tools/home/tmp/test_for_loop')

def test_while_loop_reg_infer(tmpdir):
    @gear(hdl={'compile': True})
    async def test() -> Uint[32]:
        cnt: Uint[10] = 0
        while cnt != 10:
            yield cnt
            cnt += 1

    directed(f=test(), ref=list(range(10))*3)
    sim('/tools/home/tmp/test', timeout=30)


# @gear(hdl={'compile': True})
# async def test(din: Uint[32]) -> Queue[Uint[32]]:
#     last = False
#     while not last:
#         async with din as d:
#             last = (d == 4)
#             yield d, last

# from pygears.hdl import hdlgen
# hdlgen(test(Intf(Uint[32])), outdir='/tools/home/tmp/test')

# from pygears.sim import sim
# from pygears.lib import collect

# res = []
# test() | collect(result = res)
# sim('/tools/home/tmp/test', timeout=30)
# print(res)
