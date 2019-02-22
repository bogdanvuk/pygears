from pygears import gear
from pygears.typing import Queue, Uint, bitw


@gear(svgen={'compile': True})
async def trr_dist(din: Queue, *, lvl=1,
                   dout_num) -> b'(Queue[din.data, din.lvl - 1], ) * dout_num':

    i = Uint[bitw(dout_num)](0)

    while 1:
        async with din as val:

            out_res = [None] * dout_num
            out_res[i] = val.sub()
            yield out_res

            if all(val.eot):
                i = 0
            elif all(val.eot[:lvl]):
                if i == (dout_num - 1):
                    i = 0
                else:
                    i += 1
