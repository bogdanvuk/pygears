from pygears import gear
from pygears.conf import gear_log
from pygears.typing import Queue


def trr_dist_type(dtype, rr_type):
    return Queue[dtype[0], dtype.lvl]


@gear
async def trr_dist(din: Queue, *, lvl=1, dout_num
                   ) -> b'(Queue[din.data, din.lvl - 1], ) * dout_num':
    t_din = din.dtype

    for i in range(dout_num):
        out_res = [None] * dout_num
        val = t_din(0, 0)

        while (val.eot[0] == 0):
            async with din as val:
                out_res[i] = val.sub()
                gear_log().debug(
                    f'Trr_dist yielding on output {i} value {out_res[i]}')
                yield tuple(out_res)

        if all(val.eot):
            gear_log().debug(f'Trr_dist reset to first output')
            break
