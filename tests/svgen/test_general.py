from pygears import clear, bind, Intf, gear, hier
from pygears.typing import Uint
from pygears.svgen import svgen_connect, svgen_inst, svgen
from pygears.svgen.generate import TemplateEnv
from nose import with_setup
from . import equal_on_nonspace

test_hier_module_gen_sv_ref = """
module top(
    input clk,
    input rst,
    dti.consumer top_din1, // u1 (1)
    dti.consumer top_din2, // u2 (2)
    dti.producer top_ret1, // u2 (2)
    dti.producer top_ret2 // u2 (2)

);

    dti #(.W_DATA(2)) fgear0_if_s(); // u2 (2)
    dti #(.W_DATA(2)) fgear0_if_s_bc[1:0](); // u2 (2)
    bc #(
                .SIZE(2)
    )
     bc_fgear0 (
        .clk(clk),
        .rst(rst),
        .din(fgear0_if_s),
        .dout(fgear0_if_s_bc)
    );

    connect connect_fgear0_if_s_0 (
        .clk(clk),
        .rst(rst),
        .din(fgear0_if_s_bc[0]),
        .dout(top_ret1)
    );


    dti #(.W_DATA(2)) top_din2_bc[1:0](); // u2 (2)
    bc #(
                .SIZE(2)
    )
     bc_top_din2 (
        .clk(clk),
        .rst(rst),
        .din(top_din2),
        .dout(top_din2_bc)
    );


    fgear0 fgear0_i (
        .clk(clk),
        .rst(rst),
        .arg1(top_din1),
        .arg2(top_din2_bc[0]),
        .ret(fgear0_if_s)
    );


    fgear1 fgear1_i (
        .clk(clk),
        .rst(rst),
        .arg1(fgear0_if_s_bc[1]),
        .arg2(top_din2_bc[1]),
        .ret(top_ret2)
    );

endmodule
"""


@with_setup(clear)
def test_hier_module_gen():
    @gear
    def fgear(arg1, arg2) -> {'ret': Uint[2]}:
        pass

    @hier(outnames=['top_ret1', 'top_ret2'])
    def top(top_din1, top_din2):

        ret1 = fgear(top_din1, top_din2)
        ret2 = fgear(ret1, top_din2)

        return ret1, ret2

    top(Intf(Uint[1]), Intf(Uint[2]))

    # from pygears.util.print_hier import print_hier
    # print_hier()

    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['top'].get_module(TemplateEnv()),
                             test_hier_module_gen_sv_ref)
