from pygears import gear, StopGear
from pygears.sim.type_seq import type_seq, scv_compile
from pygears.typing import TLM


@gear
async def seq(*, t, cons, outdir) -> TLM['t']:
    seqlib = scv_compile(outdir, 'seq', cons)

    yield type_seq(t, cons['vars'], seqlib)

    raise StopGear


# class SimSeqPlugin(SimInstPlugin):
#     @classmethod
#     def bind(cls):
#         cls.registry['SimInstNamespace'][seq] =
#         cls.registry['SVGenModuleNamespace'][cart] = SVGenCart
