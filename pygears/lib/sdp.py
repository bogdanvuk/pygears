from pygears import gear, module, find
from pygears.lib import dreg
from pygears.typing import Tuple, Uint
from pygears.sim import clk

TWrDin = Tuple[{'addr': Uint['w_addr'], 'data': 'w_data'}]
TRdDin = Uint['w_addr']


@gear
async def sdp_wr_port(din, *, depth, mem) -> None:
    async with din as (addr, data):
        mem[int(addr)] = data


@gear
async def sdp_rd_port(addr, *, t, depth, mem) -> b't':
    while True:
        a = await addr.get()
        dout = mem[int(a)]
        await clk()
        yield dout


@gear(outnames=['rd_data'], hdl={'hierarchical': False}, enablement=b'latency not in [0, 2]')
def sdp(wr_addr_data: TWrDin,
        rd_addr: TRdDin,
        *,
        depth=b'2**w_addr',
        w_data=b'w_data',
        w_addr=b'w_addr',
        latency=1,
        mem=None) -> b'w_data':
    """Short for Simple Dual-Port RAM. Supports simultaneous read and write
    operations i.e. ``rd_addr`` interface reads from the RAM while the
    ``wr_addr_data`` interface writes to it. It has a sigle output interface
    for read data called ``rd_data``. Since the memory doesn't use the DTI,
    adapters are needed to convert the DTI protocol to the memory interface.
    The gear consists of three submodules implemented in SystemVerilog.

    Write port adapter for the SDP RAM is called ``sdp_wr_port``. It translates
    the DTI interface to the appropriate SDP signals. The ``data`` and ``addr``
    fields of the :class:`Tuple` type are passed to the `addr` and `data` inputs
    of the memory while `valid` is used as enable input to the memory.

    Read port adapter for the SDP RAM is called ``sdp_rd_port``. It translates
    the DTI interface to the appropriate SDP signals. Data from the input
    interface is used as an address for the memory and the read data is passed
    to the output interface. Control logic is implemented for correct generation
    of all `ready` and `valid` signals for the input and output interfaces.

    The third submodule called ``sdp_mem`` is the memory itself.

    Args:
        w_data: Width of the data bus
        w_addr: Width of the address bus
        depth: Depth of the memory

    Returns:
        Data read from the memory. Same type as the ``data`` field of the
          ``TWrDin`` :class:`Tuple` i.e. the data beeing writen to memory.
    """

    if mem is None:
        mem = {}

    wr_addr_data | sdp_wr_port(depth=depth, mem=mem)
    return rd_addr | sdp_rd_port(t=wr_addr_data.dtype['data'], depth=depth, mem=mem)
