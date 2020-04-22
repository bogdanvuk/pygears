import pytest
from pygears.lib import tdp, priority_mux, verif, ccat
from pygears.lib.tdp import TWrReq
from pygears.lib.delay import delay_rng, delay_gen
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Bool, Uint, Union


@pytest.mark.parametrize('wr0_delay', [0, 5])
@pytest.mark.parametrize('rd0_delay', [0, 5])
@pytest.mark.parametrize('wr1_delay', [0, 5])
@pytest.mark.parametrize('rd1_delay', [0])
@pytest.mark.parametrize('dout_delay', [0, 5])
@pytest.mark.parametrize('depth', [4, 8])
def test_directed(
    wr0_delay,
    rd0_delay,
    wr1_delay,
    rd1_delay,
    dout_delay,
    depth,
):
    def wr0_delay_gen():
        for _ in range(depth):
            yield 0

        while True:
            yield wr0_delay

    w_addr = 3
    w_data = 8
    wr_req_t = TWrReq[w_addr, Uint[w_data]]
    rd_req_t = Uint[w_addr]
    req_t = Union[rd_req_t, wr_req_t]

    wr0_req_seq = [(i, i * 2) for i in range(depth)]

    wr0_init_seq = [(i, 0) for i in range(depth)]

    rd0_req_seq = list(range(depth))
    rd1_req_seq = list(range(depth))

    wr0_req = drv(t=wr_req_t, seq=wr0_init_seq + wr0_req_seq) \
        | delay_gen(f=wr0_delay_gen())

    rd0_req = drv(t=Uint[w_addr], seq=rd0_req_seq) \
        | delay_gen(f=iter([depth])) \
        | delay_rng(0, rd0_delay)

    req0 = priority_mux(rd0_req, wr0_req)

    req1 = ccat(drv(t=Uint[w_addr], seq=rd1_req_seq) \
                | req_t.data \
                | delay_gen(f=iter([depth])) \
                | delay_rng(0, rd1_delay)
                , Bool(False)) | req_t

    from pygears.sim.modules import SimVerilated
    verif(
        req0,
        req1,
        f=tdp(name='dut', sim_cls=SimVerilated, depth=depth),
        ref=tdp(depth=depth),
        delays=[delay_rng(0, dout_delay), delay_rng(0, 0)])

    sim()
