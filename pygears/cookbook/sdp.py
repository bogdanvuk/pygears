from pygears import gear
from pygears.typing import Tuple, Uint

TWrDin = Tuple[Uint['w_addr'], 'w_data']
TRdDin = Uint['w_addr']

depth = 3 * 224 * 16


@gear(
    outnames=['rd_data_if'],
    )
    # sv_param_kwds=['depth', 'w_data', 'w_addr'],
    # sv_submodules=['sdp_mem', 'sdp_rd_port', 'sdp_wr_port'])
def sdp_rd_port(rd_addr_if: TRdDin, *, w_data,
                depth=depth) -> b'w_data':
    pass


@gear
def sdp_wr_port(wr_addr_data_if: TWrDin) -> None:
    pass


@gear
def sdp(wr_addr_data_if: TWrDin, rd_addr_if: TRdDin, *,
        w_data=b'w_data', w_addr=b'w_addr', depth=5) -> b'w_data':
    pass
