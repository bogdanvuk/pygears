from pygears import gear
from pygears.typing import Array, Tuple, Uint
from pygears.sim import clk


@gear
async def strb_combiner(din: Tuple[{'data': Array['data_t', 'num'], 'strb': Uint}]) -> b'din["data"]':
    data_t = din.dtype['data'].data
    num = len(din.dtype['data'])

    data = Array[data_t, num]()
    last = False

    while not last:
        async with din as (d, strb):
            for i in range(num):
                if strb[i]:
                    data[i] = d[i]

            last = strb[-1]

    await clk()
    yield data


# import sys
# sys.setrecursionlimit(1500)
# # array_t = Array[Uint[8], 4]
# # strb_t = Uint[4]
# # seq = [((1, 2, 3, 4), 0x3), ((5, 6, 7, 8), 0xc)]

# array_t = Array[Uint[8], 64]
# strb_t = Uint[64]
# seq = [(list(range(64)), (1<<32) - 1), (list(range(64, 128)), ((1<<32) - 1) << 32)]


# res = []
# drv(t=Tuple[array_t, strb_t], seq=seq) \
#     | strb_combiner \
#     | collect(result=res)

# cosim('/strb_combiner', 'verilator')
# sim()

# breakpoint()
