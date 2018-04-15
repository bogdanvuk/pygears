from nose import with_setup

from pygears import Intf, Queue, Uint, clear, bind, Unit, registry
from pygears.svgen import svgen_connect, svgen_inst, svgen
from pygears.common.cart import cart_sync
from pygears.svgen.generate import TemplateEnv
# from . import equal_on_nonspace


@with_setup(clear)
def test_general():
    cart_sync(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))

    bind('SVGenFlow', registry('SVGenFlow')[:-1])

    svtop = svgen()
    # from pygears.util.print_hier import print_hier
    # print_hier(svtop)
    print(svtop['cart_sync'].get_module(TemplateEnv()))
    print(svtop['cart_sync/unzip'].get_module(TemplateEnv()))
    # print(svtop['cart_sync/sieve_2'].get_module(TemplateEnv()))
    # print(svtop['cart_sync/czip'].get_module(TemplateEnv()))
    # print(svtop['cart_sync/czip/sieve_0_3_1_2_4'].get_module(TemplateEnv()))

    # assert equal_on_nonspace(svtop['cart_sync'].get_module(TemplateEnv()),
    #                          test_cart_sync_general_sv_ref)


bind('ErrReportLevel', 0)
test_general()
