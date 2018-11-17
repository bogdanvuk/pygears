from pygears import gear, Intf, find
from pygears.typing import Integer, Tuple, Uint, Union, Queue
from pygears.common import add, filt
from pygears.cookbook import qcnt
from pygears.svgen.svcompile import compile_gear_body
from pygears.util.test_utils import equal_on_nonspace

simple_add_res = """always_comb begin
    din.ready = 1;
    dout.valid = 0;

    if (din.valid) begin
        din.ready = dout.ready;
        dout.valid = 1;
        dout_s = 11'(din_s.f0) + 11'(din_s.f1);
    end
end"""


def test_simple_add():
    add(Intf(Tuple[Uint[8], Uint[10]]))

    res = compile_gear_body(find('/add'))
    assert equal_on_nonspace(res, simple_add_res)


simple_filt_res = """always_comb begin
    din.ready = 1;
    dout.valid = 0;

    if (din.valid) begin
        if (din_s.data.ctrl == din_s.sel) begin
            din.ready = dout.ready;
            dout.valid = 1;
            dout_s = din_s.data;
        end
    end
end
"""


def test_simple_filt():
    filt(Intf(Tuple[Union[Uint[1], Uint[8], Uint[10]], Uint[2]]))
    res = compile_gear_body(find('/filt'))
    assert equal_on_nonspace(res, simple_filt_res)


simple_qcnt_res = """
typedef logic [15:0] cnt_t; // u16

logic cnt_en;
logic cnt_rst;
cnt_t cnt_reg, cnt_next;


always_ff @(posedge clk) begin
    if(rst | cnt_rst) begin
        cnt_reg = 0;
    end else if (cnt_en) begin
        cnt_reg = cnt_next;
    end
end

always_comb begin
    // Gear idle states
    din.ready = 1;
    dout.valid = 0;
    cnt_en = 1;
    cnt_rst = 0;
    cnt_next = cnt_reg;

    if (din.valid) begin
        // Gear reset conditions
        cnt_rst = dout.ready && &din_s.eot;

        // Cycle done conditions
        din.ready = dout.ready;
        cnt_en = dout.ready;

        cnt_next = 17'(cnt_reg) + 17'(1);
        dout.valid = 1;
        dout_s = {&(din_s.eot), cnt_next};
    end
end
"""


def test_simple_qcnt():
    qcnt(Intf(Queue[Uint[8]]))
    res = compile_gear_body(find('/qcnt'))
    assert equal_on_nonspace(res, simple_qcnt_res)


# from pygears.typing import Queue, Uint
# from pygears.cookbook import qcnt
# from pygears.svgen import svgen

# @gear(svgen={'compile': True})
# async def svctest(din: Queue, *, lvl=1, w_out=16) -> Queue[Uint['w_out']]:
#     cnt = Uint[w_out](0)
#     async for (data, eot) in din:
#         if all(eot[:din.dtype.lvl - lvl]):
#             cnt = cnt + 1
#             yield (cnt, all(eot))

# svctest(Intf(Queue[Uint[8]]))
# res = compile_gear_body(find('/svctest'))
# print(res)
# svgen('/svctest', outdir='/tools/home/tmp')

# from pygears.sim import sim
# from pygears.cookbook.verif import verif
# from pygears.sim.modules.drv import drv
# from pygears.sim.modules.verilator import SimVerilated
# from pygears.cookbook.delay import delay_rng
# from pygears.sim.extens.vcd import VCD
# from pygears import bind

# seq = [list(range(10)), list(range(5))]

# bind('svgen/debug_intfs', ['*'])
# bind('logger/sim/error', lambda x: x)

# report = verif(
#     drv(t=Queue[Uint[8]], seq=seq) | delay_rng(2, 2),
#     f=svctest(sim_cls=SimVerilated, lvl=1),
#     ref=svctest(name='ref_model', upper=2),
#     delays=[delay_rng(5, 5)]
#     )

# sim(outdir='/tools/home/tmp', extens=[])

# print(report)
