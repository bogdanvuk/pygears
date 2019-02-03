from pygears import Intf, find
from pygears.typing import Queue, Tuple, Uint, Union
from pygears.common import add, filt, invert
from pygears.cookbook import qcnt, replicate, accumulator, take
from pygears.svgen.svcompile import compile_gear_body
from pygears.util.test_utils import equal_on_nonspace

simple_add_res = """
logic exit_cond_block_1;
logic exit_cond_block_2;
always_comb begin
    dout.valid = 0;
    dout_s = 11'(11'(din_s.f0) + 11'(din_s.f1));
    if (din.valid) begin
        dout.valid = 1;
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid) begin
        din.ready = exit_cond_block_1;
    end
end
assign exit_cond_block_1 = exit_cond_block_2;
assign exit_cond_block_2 = dout.ready;
"""


def test_simple_add():
    add(Intf(Tuple[Uint[8], Uint[10]]))
    res = compile_gear_body(find('/add'))
    assert equal_on_nonspace(res, simple_add_res)


simple_filt_res = """
logic exit_cond_block_1;
logic exit_cond_block_2;
logic exit_cond_block_3;
always_comb begin
    dout.valid = 0;
    dout_s = 12'(din_s.data);
    if (din.valid) begin
        if (din_s.data.ctrl == din_s.sel) begin
            dout.valid = 1;
        end
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid) begin
        din.ready = exit_cond_block_1;
    end
end
assign exit_cond_block_1 = exit_cond_block_2;
assign exit_cond_block_2 = !(din_s.data.ctrl == din_s.sel) || ((din_s.data.ctrl == din_s.sel) && exit_cond_block_3);
assign exit_cond_block_3 = dout.ready;
"""


def test_simple_filt():
    filt(Intf(Tuple[Union[Uint[1], Uint[8], Uint[10]], Uint[2]]))
    res = compile_gear_body(find('/filt'))
    assert equal_on_nonspace(res, simple_filt_res)


simple_qcnt_res = """
typedef logic [15:0] cnt_t; // u16
logic cnt_en;
cnt_t cnt_reg, cnt_next;
logic cycle_cond_block_1;
logic cycle_cond_block_2;
logic exit_cond_block_1;
logic exit_cond_block_2;
logic rst_cond;
assign rst_cond = exit_cond_block_1 && din.valid;
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        cnt_reg = 1;
    end else if (cnt_en) begin
        cnt_reg = cnt_next;
    end
end
always_comb begin
    cnt_en = 0;
    cnt_next = 16'(17'(cnt_reg) + 17'(1));
    if (din.valid) begin
        cnt_en = cycle_cond_block_1;
    end
end
always_comb begin
    dout.valid = 0;
    dout_s = {1'(&(din_s.eot)), 16'(cnt_reg)};
    if (din.valid) begin
        dout.valid = 1;
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid) begin
        din.ready = cycle_cond_block_1;
    end
end
assign cycle_cond_block_1 = cycle_cond_block_2;
assign exit_cond_block_1 = &din_s.eot && exit_cond_block_2;
assign cycle_cond_block_2 = dout.ready;
assign exit_cond_block_2 = dout.ready;
"""


def test_simple_qcnt():
    qcnt(Intf(Queue[Uint[8]]))
    res = compile_gear_body(find('/qcnt'))
    assert equal_on_nonspace(res, simple_qcnt_res)


simple_invert_res = """
logic exit_cond_block_1;
logic exit_cond_block_2;
always_comb begin
    dout.valid = 0;
    dout_s = 4'(~(din_s));
    if (din.valid) begin
        dout.valid = 1;
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid) begin
        din.ready = exit_cond_block_1;
    end
end
assign exit_cond_block_1 = exit_cond_block_2;
assign exit_cond_block_2 = dout.ready;
"""


def test_simple_invert():
    invert(Intf(Uint[4]))
    res = compile_gear_body(find('/invert'))
    assert equal_on_nonspace(res, simple_invert_res)


simple_replicate_res = """
typedef logic [15:0] i_t; // u16
logic i_en;
i_t i_reg, i_next;
typedef logic [0:0] last_t; // u1
last_t last_v;
logic cycle_cond_block_2;
logic cycle_cond_block_3;
logic exit_cond_block_1;
logic exit_cond_block_2;
logic exit_cond_block_3;
logic rst_cond;
assign rst_cond = exit_cond_block_1 && din.valid;
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        i_reg = 0;
    end else if (i_en) begin
        i_reg = i_next;
    end
end
always_comb begin
    i_en = 0;
    i_next = 16'(17'(i_reg) + 17'(1));
    if (din.valid) begin
        i_en = cycle_cond_block_2;
    end
end
always_comb begin
    last_v = 1'(i_next >= din_s.f0);
end
always_comb begin
    dout.valid = 0;
    dout_s = {1'(last_v), 16'(din_s.f1)};
    if (din.valid) begin
        dout.valid = 1;
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid) begin
        din.ready = exit_cond_block_1;
    end
end
assign exit_cond_block_1 = exit_cond_block_2;
assign cycle_cond_block_2 = cycle_cond_block_3;
assign exit_cond_block_2 = cycle_cond_block_3 && (last_v && exit_cond_block_3);
assign cycle_cond_block_3 = dout.ready;
assign exit_cond_block_3 = dout.ready;
"""


def test_simple_replicate():
    replicate(Intf(Tuple[Uint[16], Uint[16]]))
    res = compile_gear_body(find('/replicate'))
    assert equal_on_nonspace(res, simple_replicate_res)


simple_accumulator_res = """
typedef logic [15:0] acc_t; // u16
logic acc_en;
acc_t acc_reg, acc_next;
typedef logic [0:0] offset_added_t; // u1
logic offset_added_en;
offset_added_t offset_added_reg, offset_added_next;
typedef logic [0:0] state_t; // u1
logic state_en;
state_t state_reg, state_next;
logic exit_cond_block_1;
logic exit_cond_block_2;
logic rst_cond;
assign rst_cond = exit_cond_block_2 && (state_reg == 1);
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        acc_reg = 0;
    end else if (acc_en) begin
        acc_reg = acc_next;
    end
end
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        offset_added_reg = 0;
    end else if (offset_added_en) begin
        offset_added_reg = offset_added_next;
    end
end
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        state_reg = 0;
    end else if (state_en) begin
        state_reg = state_next;
    end
end
always_comb begin
    acc_en = 0;
    offset_added_en = 0;
    acc_next = 16'(17'(acc_reg) + 17'(din_s.data.data));
    offset_added_next = 1'(1);
    if (din.valid && (state_reg == 0)) begin
        if (offset_added_reg) begin
            acc_en = 1;
        end
        if (!(offset_added_reg)) begin
            acc_en = 1;
            acc_next = 16'(17'(din_s.data.offset) + 17'(din_s.data.data));
            offset_added_en = 1;
        end
    end
end
always_comb begin
    dout.valid = 0;
    dout_s = 16'(acc_reg);
    if (state_reg == 1) begin
        dout.valid = 1;
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid && (state_reg == 0)) begin
        din.ready = 1;
    end
end
always_comb begin
    state_en = 0;
    state_next = 1;
    if (din.valid && (state_reg == 0)) begin
        state_en = exit_cond_block_1;
    end
end
assign exit_cond_block_1 = &din_s.eot;
assign exit_cond_block_2 = dout.ready;
"""


def test_simple_accumulator():
    accumulator(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
    res = compile_gear_body(find('/accumulator'))
    assert equal_on_nonspace(res, simple_accumulator_res)


simple_take_res = """
typedef logic [0:0] pass_eot_t; // u1
logic pass_eot_en;
pass_eot_t pass_eot_reg, pass_eot_next;
typedef logic [15:0] cnt_t; // u16
logic cnt_en;
cnt_t cnt_reg, cnt_next;
typedef logic [0:0] last_t; // u1
last_t last_v;
logic cycle_cond_block_1;
logic cycle_cond_block_2;
logic cycle_cond_block_3;
logic exit_cond_block_1;
logic exit_cond_block_2;
logic exit_cond_block_3;
logic rst_cond;
assign rst_cond = exit_cond_block_1 && din.valid;
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        pass_eot_reg = 1;
    end else if (pass_eot_en) begin
        pass_eot_reg = pass_eot_next;
    end
end
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        cnt_reg = 1;
    end else if (cnt_en) begin
        cnt_reg = cnt_next;
    end
end
always_comb begin
    pass_eot_en = 0;
    cnt_en = 0;
    pass_eot_next = 1'(0);
    cnt_next = 16'(17'(cnt_reg) + 17'(1));
    if (din.valid) begin
        cnt_en = cycle_cond_block_1 && exit_cond_block_2;
        if (last_v) begin
            pass_eot_en = cycle_cond_block_1 && exit_cond_block_2;
        end
    end
end
always_comb begin
    last_v = 1'((cnt_reg == din_s.data.f1) && pass_eot_reg);
end
always_comb begin
    dout.valid = 0;
    dout_s = {1'(din_s.eot || last_v), 16'(din_s.data.f0)};
    if (din.valid) begin
        if ((cnt_reg <= din_s.data.f1) && pass_eot_reg) begin
            dout.valid = 1;
        end
    end
end
always_comb begin
    din.ready = 0;
    if (din.valid) begin
        din.ready = cycle_cond_block_1;
    end
end
assign cycle_cond_block_1 = cycle_cond_block_2;
assign exit_cond_block_1 = &din_s.eot && exit_cond_block_2;
assign cycle_cond_block_2 = !((cnt_reg <= din_s.data.f1) && pass_eot_reg) || (((cnt_reg <= din_s.data.f1) && pass_eot_reg) && cycle_cond_block_3);
assign exit_cond_block_2 = !((cnt_reg <= din_s.data.f1) && pass_eot_reg) || (((cnt_reg <= din_s.data.f1) && pass_eot_reg) && exit_cond_block_3);
assign cycle_cond_block_3 = dout.ready;
assign exit_cond_block_3 = dout.ready;
"""


def test_simple_take():
    take(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
    res = compile_gear_body(find('/take'))
    assert equal_on_nonspace(res, simple_take_res)
