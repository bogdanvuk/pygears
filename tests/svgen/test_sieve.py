from nose import with_setup

from pygears import Intf, Uint, bind, clear
from pygears.svgen import svgen, svgen_connect, svgen_inst
from pygears.svgen.generate import TemplateEnv

from . import equal_on_nonspace

test_general_ref = """
module conv_0v2_7_8v10
(
    input clk,
    input rst,
    dti.consumer din, // u10 (10)
    dti.producer dout // u5 (5)

);
   assign dout.data = {din.data[9:8], din.data[7], din.data[1:0]};
   assign dout.valid = din.valid;
   assign din.ready  = dout.ready;

endmodule
"""


@with_setup(clear)
def test_general():
    Intf(Uint[10])[:2, 7, 8:]

    bind('ErrReportLevel', 0)
    bind('SVGenFlow', [svgen_inst, svgen_connect])
    svtop = svgen()
    assert equal_on_nonspace(svtop['conv_0v2_7_8v10'].get_module(
        TemplateEnv()), test_general_ref)
