from pygears import Intf, find
from pygears.typing import Queue, Tuple, Uint, Union
from pygears.common import add, filt, invert
from pygears.cookbook import qcnt, replicate, accumulator, take
from pygears.svgen.svcompile import compile_gear_body
from pygears.util.test_utils import equal_on_nonspace

simple_add_res = """
always_comb begin
    dout.valid = 1'(0);
    dout_s = 11'(11'(din_s.f0) + 11'(din_s.f1));
    if (din.valid) begin
        dout.valid = 1'(1);
    end
end
always_comb begin
    din.ready = 1'(0);
    if (din.valid) begin
        din.ready = 1'(dout.ready);
    end
end
"""


def test_simple_add():
    add(Intf(Tuple[Uint[8], Uint[10]]))

    res = compile_gear_body(find('/add'))
    assert equal_on_nonspace(res, simple_add_res)


simple_filt_res = """
always_comb begin
    dout.valid = 1'(0);
    dout_s = 12'(din_s.data);
    if (din.valid) begin
        if (din_s.data.ctrl == din_s.sel) begin
            dout.valid = 1'(1);
        end
    end
end
always_comb begin
    din.ready = 1'(0);
    if (din.valid) begin
        din.ready = 1'(1);
        if (din_s.data.ctrl == din_s.sel) begin
            din.ready = 1'(dout.ready);
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
        cnt_reg = 1;
    end else if (cnt_en) begin
        cnt_reg = cnt_next;
    end
end

always_comb begin
    cnt_en = 1'(0);
    cnt_rst = 1'(0);
    cnt_next = 16'(17'(cnt_reg) + 17'(1));
    if (din.valid) begin
        cnt_rst = 1'(dout.ready && &din_s.eot);
        cnt_en = 1'(dout.ready);
    end
end

always_comb begin
    dout.valid = 1'(0);
    dout_s = 17'({&(din_s.eot), cnt_reg});
    if (din.valid) begin
        dout.valid = 1'(1);
    end
end

always_comb begin
    din.ready = 1'(0);
    if (din.valid) begin
        din.ready = 1'(dout.ready);
    end
end
"""


def test_simple_qcnt():
    qcnt(Intf(Queue[Uint[8]]))
    res = compile_gear_body(find('/qcnt'))
    assert equal_on_nonspace(res, simple_qcnt_res)


simple_invert_res = """
always_comb begin
    dout.valid = 1'(0);
    dout_s = 4'(~ din_s);
    if (din.valid) begin
        dout.valid = 1'(1);
    end
end

always_comb begin
    din.ready = 1'(0);
    if (din.valid) begin
        din.ready = 1'(dout.ready);
    end
end
"""


def test_simple_invert():
    invert(Intf(Uint[4]))
    res = compile_gear_body(find('/invert'))
    assert equal_on_nonspace(res, simple_invert_res)


simple_replicate_res = """
typedef logic [15:0] i_t; // u16

logic i_en;
logic i_rst;
i_t i_reg, i_next;

typedef logic [0:0] last_t; // u1
last_t last_v;

always_ff @(posedge clk) begin
    if(rst | i_rst) begin
        i_reg = 0;
    end else if (i_en) begin
        i_reg = i_next;
    end
end

always_comb begin
    i_en = 1'(0);
    i_rst = 1'(0);
    i_next = 16'(17'(i_reg) + 17'(1));
    if (din.valid) begin
        i_rst = 1'(dout.ready && last_v);
        i_en = 1'(dout.ready);
    end
end

always_comb begin
    last_v = 1'(i_next >= din_s.f0);
end

always_comb begin
    dout.valid = 1'(0);
    dout_s = 17'({last_v, din_s.f1});
    if (din.valid) begin
        dout.valid = 1'(1);
    end
end

always_comb begin
    din.ready = 1'(0);
    if (din.valid) begin
        din.ready = 1'(dout.ready);
        din.ready = 1'(dout.ready && last_v);
    end
end
"""


def test_simple_replicate():
    replicate(Intf(Tuple[Uint[16], Uint[16]]))
    res = compile_gear_body(find('/replicate'))
    assert equal_on_nonspace(res, simple_replicate_res)


simple_accumulator_res = """
typedef logic [15:0] acc_t; // u16

logic acc_en;
logic acc_rst;
acc_t acc_reg, acc_next;

typedef logic [0:0] offset_added_t;
logic offset_added_en;
logic offset_added_rst;
offset_added_t offset_added_reg, offset_added_next;

typedef logic [1:0] state_t; // u2

logic state_en;
logic state_rst;
state_t state_reg, state_next;

always_ff @(posedge clk) begin
    if(rst | acc_rst) begin
        acc_reg = 0;
    end else if (acc_en) begin
        acc_reg = acc_next;
    end
end

always_ff @(posedge clk) begin
    if(rst | offset_added_rst) begin
        offset_added_reg = 0;
    end else if (offset_added_en) begin
        offset_added_reg = offset_added_next;
    end
end

always_ff @(posedge clk) begin
    if(rst | state_rst) begin
        state_reg = 0;
    end else if (state_en) begin
        state_reg = state_next;
    end
end

always_comb begin
    acc_en = 1'(0);
    acc_rst = 1'(0);
    acc_next = 16'(17'(acc_reg) + 17'(din_s.data.f0));
    if ((state_reg == 0) && (din.valid)) begin
        if (offset_added_reg) begin
            acc_en = 1'(1);
        end
        else begin
            acc_en = 1'(1);
            acc_next = 16'(17'(din_s.data.f1) + 17'(din_s.data.f0));
        end
    end
    if ((state_reg == 1)) begin
        acc_rst = 1'(dout.ready);
    end
end

always_comb begin
    offset_added_en = 1'(0);
    offset_added_rst = 1'(0);
    offset_added_next = 1'(1);
    if ((state_reg == 0) && (din.valid)) begin
        if (!(offset_added_reg)) begin
            offset_added_en = 1'(1);
        end
    end
    if ((state_reg == 1)) begin
        offset_added_rst = 1'(dout.ready);
    end
end

always_comb begin
    state_en = 1'(0);
    state_rst = 1'(0);
    state_next = 2'(3'(state_reg) + 3'(1));
    if ((state_reg == 0) && (din.valid)) begin
        if (&din_s.eot) begin
            state_en = 1'(1);
        end
    end
    if ((state_reg == 1)) begin
        state_rst = 1'(dout.ready);
    end
end

always_comb begin
    dout.valid = 1'(0);
    dout_s = 16'(acc_reg);
    if ((state_reg == 1)) begin
        dout.valid = 1'(1);
    end
end

always_comb begin
    din.ready = 1'(0);
    if ((state_reg == 0) && (din.valid)) begin
        din.ready = 1'(1);
    end
end
"""


def test_simple_accumulator():
    accumulator(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
    res = compile_gear_body(find('/accumulator'))
    assert equal_on_nonspace(res, simple_accumulator_res)


simple_take_res = """
typedef logic [0:0] pass_eot_t; // u1
logic pass_eot_en;
logic pass_eot_rst;
pass_eot_t pass_eot_reg, pass_eot_next;
typedef logic [15:0] cnt_t; // u16
logic cnt_en;
logic cnt_rst;
cnt_t cnt_reg, cnt_next;
typedef logic [0:0] last_t; // u1
last_t last_v;


always_ff @(posedge clk) begin
    if(rst | pass_eot_rst) begin
        pass_eot_reg = 1;
    end else if (pass_eot_en) begin
        pass_eot_reg = pass_eot_next;
    end
end

always_ff @(posedge clk) begin
    if(rst | cnt_rst) begin
        cnt_reg = 1;
    end else if (cnt_en) begin
        cnt_reg = cnt_next;
    end
end

always_comb begin
    pass_eot_en = 1'(0);
    pass_eot_rst = 1'(0);
    pass_eot_next = 1'(0);
    if (din.valid) begin
        pass_eot_rst = 1'(&din_s.eot);
        if (cnt_reg <= din_s.data.f1 && pass_eot_reg) begin
            pass_eot_rst = 1'(dout.ready && &din_s.eot);
        end
        if (last_v) begin
            pass_eot_en = 1'(1);
        end
    end
end

always_comb begin
    cnt_en = 1'(0);
    cnt_rst = 1'(0);
    cnt_next = 16'(17'(cnt_reg) + 17'(1));
    if (din.valid) begin
        cnt_rst = 1'(&din_s.eot);
        cnt_en = 1'(1);
        if (cnt_reg <= din_s.data.f1 && pass_eot_reg) begin
            cnt_rst = 1'(dout.ready && &din_s.eot);
        end
    end
end

always_comb begin
    last_v = 1'(cnt_reg == din_s.data.f1 && pass_eot_reg);
end

always_comb begin
    dout.valid = 1'(0);
    dout_s = 17'({din_s.eot || last_v, din_s.data.f0});
    if (din.valid) begin
        if (cnt_reg <= din_s.data.f1 && pass_eot_reg) begin
            dout.valid = 1'(1);
        end
    end
end

always_comb begin
    din.ready = 1'(0);
    if (din.valid) begin
        din.ready = 1'(1);
        if (cnt_reg <= din_s.data.f1 && pass_eot_reg) begin
            din.ready = 1'(dout.ready);
        end
        else begin
            din.ready = 1'(1);
        end
    end
end
"""


def test_simple_take():
    take(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
    res = compile_gear_body(find('/take'))
    assert equal_on_nonspace(res, simple_take_res)


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
