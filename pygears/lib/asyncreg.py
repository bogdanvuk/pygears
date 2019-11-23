from pygears import gear
from pygears.typing import Maybe, Tuple, Uint, Union
from .mux import mux
from .demux import demux
from .ccat import ccat
from .shred import shred
from .union import union_collapse


@gear
def spy(din) -> b'din':
    pass


@gear
async def sample(din, *, latency=1, hold=1, init=None) -> b"din":
    pass


@gear(hdl={'files': ['sample.sv']})
async def trigreg(din: Maybe['data'], *, latency=1, init=None) -> b'data':
    pass


@gear
def regmap(
        wr: Tuple[{
            'addr': Uint['w_addr'],
            'data': 'data'
        }],
        *,
        addrmap,
        initmap={},
        regtype={}):

    *reqs, dflt = ccat(wr['data'], wr['addr']) \
        | Union \
        | demux(mapping=addrmap)

    dflt | shred

    douts = []
    for i, r in enumerate(reqs):
        init = initmap.get(i, None)
        type_ = regtype.get(i, sample)
        if type_.func.__name__ == 'trigreg':
            r = r >> Maybe[Uint[len(r.dtype)-1]]

        douts.append(type_(r, init=init))

    return tuple(douts)

    # rd_data = mux(rd, *tuple(spy(d) for d in douts)) \
    #     | union_collapse(t=wr.dtype[0])

    # return tuple(rd_data, *douts)
