from pygears import gear
from pygears.typing import Maybe, Tuple, Uint, Union
from .demux import demux
from .shred import shred


@gear
async def sample(din, *, latency=1, hold=1, init=None) -> b"din":
    pass


@gear(hdl={'files': ['sample.sv']})
async def trigreg(din: Maybe["data"]) -> b"data":
    pass


@gear
def regmap(wr: Tuple['data', Uint['w_addr']], *, addrmap, initmap={}, regtype={}):
    *reqs, dflt = wr | Union | demux(mapping=addrmap)

    dflt | shred

    douts = []
    for i, r in enumerate(reqs):
        init = initmap.get(i, None)
        type_ = regtype.get(i, sample)
        douts.append(type_(r, init=init))

    return tuple(douts)
