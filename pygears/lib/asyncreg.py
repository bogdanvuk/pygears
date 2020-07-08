from pygears import gear, IntfEmpty, module
from pygears.sim import clk
from pygears.typing import Maybe, Tuple, Uint, Union, Bool
from .demux import demux
from .ccat import ccat
from .shred import shred


@gear
def spy(din) -> b'din':
    pass


@gear
async def avail_spy(din) -> b'(Bool, din)':
    pass


def avail(din):
    dout0, dout1 = avail_spy(din)

    for p in din.consumers[:-1]:
        if p is dout1.producer:
            continue

        din.disconnect(p)
        dout1.connect(p)

    return dout0


@gear
async def sample(din, *, latency=1, hold=1, init=None) -> b"din":
    data = din.dtype() if init is None else din.dtype(init)
    valid = init is not None
    dout = module().dout

    while True:
        if latency == 0:
            try:
                data = din.get_nb()
                valid = True
            except IntfEmpty:
                pass

        if valid and dout.ready_nb():
            dout.put_nb(data)

            if not hold:
                valid = False

        if latency == 1:
            try:
                data = din.get_nb()
                valid = True
            except IntfEmpty:
                pass

        await clk()


@gear(hdl={'files': ['sample.sv']})
async def trigreg(din: Maybe['data'], *, latency=1, init=None) -> b'data':
    pass


@gear
def regmap(wr: Tuple[{'addr': Uint['w_addr'], 'data': 'data'}], *, addrmap, initmap={}, regtype={}):

    *reqs, dflt = ccat(wr['data'], wr['addr']) \
        | Union \
        | demux(mapping=addrmap)

    dflt | shred

    douts = []
    for i, r in enumerate(reqs):
        init = initmap.get(i, None)
        type_ = regtype.get(i, sample)
        if type_.func.__name__ == 'trigreg':
            r = r >> Maybe[Uint[len(r.dtype) - 1]]

        douts.append(type_(r, init=init))

    return tuple(douts)

    # rd_data = mux(rd, *tuple(spy(d) for d in douts)) \
    #     | union_collapse(t=wr.dtype[0])

    # return tuple(rd_data, *douts)
