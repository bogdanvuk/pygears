from pygears import gear
from pygears.typing import Queue, Unit
from pygears import module
from pygears.util.utils import quiter_async


@gear(sv_param_kwds=[], enablement=b'din_lvl >= lvl')
async def quenvelope(din: Queue['din_t', 'din_lvl'], *,
                     lvl) -> Queue[Unit, 'lvl']:
    """Extracts the queue structure of desired level called the envelope

    If there are more eot levels then forwarded to the output, those eot excess
levels are called subenvelope (which is not passed to the output). When
there is a subenvelope, the number of data the output transactions (envelope)
will contain is lowered by contracting each input transactions within
subenvelope to the length of 1. This is done in order that the envelope can be
correctly used within cartesian concatenations.

    """

    dout = module().dout
    sub_lvl = din.dtype.lvl - lvl
    out_data = None

    async for data in quiter_async(din):
        if out_data is None:
            out_data = (Unit(), data.eot[-lvl:])
            dout.put_nb(out_data)

        if sub_lvl > 0:
            subelem = data.sub(sub_lvl)
            if subelem.last:
                out_data = None
                await dout.ready()
        else:
            out_data = None
            await dout.ready()

