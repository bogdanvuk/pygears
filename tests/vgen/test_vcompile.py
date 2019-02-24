from pygears import Intf, find
from pygears.common import add, filt
from pygears.typing import Tuple, Uint, Union
from pygears.util.test_utils import equal_on_nonspace
from pygears.vgen.vcompile import compile_gear_body

SIMPLE_ADD_RES = """
wire exit_cond_block_2;
always @(*) begin
    dout_valid = 0;
    dout_s = $unsigned($unsigned({3'b0, din_s_f0}) + $unsigned({1'b0, din_s_f1}));
    if (din_valid) begin
        dout_valid = 1;
    end
end
always @(*) begin
    din_ready = 0;
    if (din_valid) begin
        din_ready = exit_cond_block_2;
    end
end
assign exit_cond_block_2 = dout_ready;
"""


def test_simple_add():
    add(Intf(Tuple[Uint[8], Uint[10]]))
    res = compile_gear_body(find('/add'))
    assert equal_on_nonspace(res, SIMPLE_ADD_RES)


simple_filt_res = """
wire exit_cond_block_2;
wire in_cond_block_2;
wire exit_cond_block_3;
always @(*) begin
    dout_valid = 0;
    dout_s = (din_s_data);
    if (din_valid) begin
        if (din_s_data_ctrl == din_s_sel) begin
            dout_valid = 1;
        end
    end
end
always @(*) begin
    din_ready = 0;
    if (din_valid) begin
        din_ready = exit_cond_block_2;
    end
end
assign exit_cond_block_2 = !(in_cond_block_2) || exit_cond_block_3;
assign in_cond_block_2 = din_s_data_ctrl == din_s_sel;
assign exit_cond_block_3 = dout_ready;
"""


def test_simple_filt():
    filt(Intf(Tuple[Union[Uint[1], Uint[8], Uint[10]], Uint[2]]))
    res = compile_gear_body(find('/filt'))
    assert equal_on_nonspace(res, simple_filt_res)
