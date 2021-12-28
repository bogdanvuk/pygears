from pygears import gear
from pygears.typing import Queue, Tuple, Uint, code, Array
from .ccat import ccat
from .czip import czip


@gear
def queue_wrap_from(din, qdin, *, fcat=czip):
    cat_data = fcat(qdin, din)

    return ccat(cat_data['data'][1], cat_data['eot']) \
        | Queue[din.dtype, qdin.dtype.lvl]


@gear
async def sot_queue(din: Queue['data', 'lvl'], *,
                    lvl=b'lvl') -> Tuple[b'din.data', b'din.eot']:
    sot = din.dtype.eot.max

    async for (data, eot) in din:
        yield (data, sot)

        neot = (~eot) << 1

        sot_arr = Array[Uint[1], lvl](None)
        for i in range(lvl):
            sot_arr[i] = eot[i] if i == 0 else sot[i] & neot[i]

        sot = code(sot_arr, Uint)
