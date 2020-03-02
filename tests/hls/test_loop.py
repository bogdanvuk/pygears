from pygears import gear, Intf
from pygears.typing import Bool, Uint, Queue
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed
from pygears.lib.rng import qrange

# @gear(hdl={'compile': True})
# async def test(din: Queue) -> b'din':
#     eot: din.dtype.eot

#     eot = din.dtype.eot(0)
#     while not all(eot):
#         async with din as (data, eot):
#             yield data, eot


def test_while_loop_reg_infer(tmpdir):
    @gear(hdl={'compile': True})
    async def test() -> Uint[32]:
        cnt = Uint[10](0)

        while cnt != 10:
            yield cnt
            cnt += 1

    directed(f=test(), ref=list(range(10)) * 3)
    cosim('/test', 'verilator')

    sim(tmpdir, timeout=30)



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
