from pygears import gear
from pygears.typing import Tuple, Uint

TWrDin = Tuple[{'addr': Uint['w_addr'], 'data': 'w_data'}]
TRdDin = Uint['w_addr']


@gear(
    outnames=['rd_data'])
def sdp(wr_addr_data: TWrDin,
        rd_addr: TRdDin,
        *,
        w_data=b'w_data',
        w_addr=b'w_addr',
        depth=5) -> b'w_data':
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
