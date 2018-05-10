from pygears import Intf, clear, gear
from pygears.typing import Uint
from nose import with_setup
from utils import svgen_check


@with_setup(clear)
@svgen_check(['top.sv'])
def test_hier_module_gen():
    @gear
    def fgear(arg1, arg2) -> {'ret': Uint[2]}:
        pass

    @gear(outnames=['top_ret1', 'top_ret2'])
    def top(top_din1, top_din2):

        ret1 = fgear(top_din1, top_din2)
        ret2 = fgear(ret1, top_din2)

        return ret1, ret2

    top(Intf(Uint[1]), Intf(Uint[2]))
