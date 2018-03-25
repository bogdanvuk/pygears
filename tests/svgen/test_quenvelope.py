from nose import with_setup

from pygears import clear, Uint, Queue, Intf, Unit, bind
from pygears.common import quenvelope
from pygears.svgen import svgen_connect, svgen_inst, svgen
from pygears.svgen.generate import TemplateEnv
from . import equal_on_nonspace

test_skip_ref = """
module quenvelope
(
    input clk,
    input rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout

);


    typedef struct packed {
        logic [1:0] out_eot;
        logic [2:0] subenvelope;
        logic [0:0] data;
    } din_t;
    typedef struct packed {
        logic [1:0] out_eot;
    } dout_t;

    din_t din_s;
    dout_t dout_s;
    assign din_s = din.data;

    assign dout_s.out_eot = din_s.out_eot;
    assign dout.data = dout_s;

    logic  handshake;
    logic  ready_reg;
    logic  subelem_done;

    assign subelem_done = &din_s.subenvelope;
    assign din.ready = (dout.ready || (!subelem_done));
    assign dout.valid = din.valid && (!ready_reg);

    assign handshake = dout.valid & dout.ready;

    always_ff @(posedge clk) begin
        if (rst) begin
          ready_reg <= 1'b0;
        end
        else begin
          if (subelem_done && handshake) begin
              ready_reg <= 1'b0;
          end
          else begin
              ready_reg <= ready_reg || handshake;
          end
        end
    end

endmodule
"""


@with_setup(clear)
def test_skip():
    quenvelope(Intf(Queue[Uint[1], 5]), lvl=2)

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['quenvelope'].get_module(TemplateEnv()),
                             test_skip_ref)


test_all_pass_ref = """
module quenvelope
(
    input clk,
    input rst,
    dti_s_if.consumer din,
    dti_s_if.producer dout

);


    typedef struct packed {
        logic [1:0] out_eot;
        logic [0:0] data;
    } din_t;
    typedef struct packed {
        logic [1:0] out_eot;
    } dout_t;

    din_t din_s;
    dout_t dout_s;
    assign din_s = din.data;

    assign dout_s.out_eot = din_s.out_eot;
    assign dout.data = dout_s;

    assign din.ready = dout.ready;
    assign dout.valid = din.valid;

endmodule
"""


@with_setup(clear)
def test_all_pass():
    quenvelope(Intf(Queue[Uint[1], 2]), lvl=2)

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['quenvelope'].get_module(TemplateEnv()),
                             test_all_pass_ref)