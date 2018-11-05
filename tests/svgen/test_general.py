from pygears import Intf, gear
from pygears.typing import Uint
from pygears.util.test_utils import svgen_check


@svgen_check(['hier.sv'])
def test_hier_module_gen():
    @gear
    def fgear(arg1, arg2) -> {'ret': Uint[2]}:
        pass

    @gear(outnames=['top_ret1', 'top_ret2'])
    def hier(top_din1, top_din2):

        ret1 = fgear(top_din1, top_din2)
        ret2 = fgear(ret1, top_din2)

        return ret1, ret2

    hier(Intf(Uint[1]), Intf(Uint[2]))
