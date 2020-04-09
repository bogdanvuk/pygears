import pytest
from pygears.util.test_utils import get_decoupled_dut
from functools import reduce as freduce
from pygears.lib import reduce, directed, drv, verif, delay_rng, accum
from pygears.typing import Uint, Queue, Bool, saturate
from pygears.sim import sim
from pygears.util.test_utils import synth_check
from pygears import Intf


def test_uint_directed(tmpdir, sim_cls):
    init = [7, 45]
    seq = [list(range(0, 100, 10)), list(range(2))]

    def add(x, y):
        return saturate(x + y, Uint[8])

    directed(drv(t=Queue[Uint[8]], seq=seq),
             drv(t=Uint[8], seq=init),
             f=reduce(f=add, sim_cls=sim_cls),
             ref=[freduce(add, s, i) for s, i in zip(seq, init)])
    sim(resdir=tmpdir)


# from pygears.sim.modules import SimVerilated
# test_uint_directed('/tools/home/tmp/reduce', SimVerilated)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_delay(tmpdir, cosim_cls, din_delay, dout_delay):
    def bitfield(n):
        return [int(digit) for digit in bin(n)[2:]]

    seq = [bitfield(0x73), bitfield(0x00)]
    init = [1, 0]

    dut = get_decoupled_dut(dout_delay, reduce(f=lambda x, y: x ^ y))
    verif(drv(t=Queue[Bool], seq=seq) | delay_rng(din_delay, din_delay),
          drv(t=Uint[8], seq=init),
          f=dut(sim_cls=cosim_cls),
          ref=reduce(name='ref_model', f=lambda x, y: x ^ y),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(resdir=tmpdir)

# from pygears.hls.ast import beniget

# c = """
# async def group(din: Queue, size: Uint, *,
#                 init=1) -> Queue['din.data', 'din.lvl + 1']:
#     cnt = size.dtype(init)
#     last: Bool
#     out_eot: Uint[din.dtype.lvl+1]

#     async with size as c:
#         assert c >= init, 'group: incorrect configuration'
#         last = False
#         while not last:
#             async for (data, eot) in din:
#                 last = (cnt == c)
#                 out_eot = last @ eot
#                 yield (data, out_eot)
#                 if not last and all(eot):
#                     cnt += 1
# """

# module = beniget.ast.parse(c)

# # compute the def-use chains at module level
# duc = beniget.DefUseChains()
# duc.visit(module)
# udc = beniget.UseDefChains(duc)

# for n, d in udc.chains.items():
#     print(f'{id(n)}: {beniget.ast.dump(n)}')
#     print(' | '.join([str(id(v.node)) for v in d]))

# # for n, d in duc.chains.items():
# #     print(f'{id(n)}: {beniget.ast.dump(n)}')
# #     print(repr(d))

# import gast
# import ast
# from pygears.hls.ast import cfg, annotations as anno


# c = """
# async def reduce(din: Queue, init, *, f) -> b'init':
#     a = 2
#     acc: init.dtype = a

#     async with init as i:
#         acc = i
#         async for (d, eot) in din:
#             bla = acc + i
#             acc = f(bla, d)

#             if eot:
#                 yield acc
# """

# node = ast.parse(c)
# cfg.forward(node, cfg.ReachingDefinitions())
# body = node.body[0].body
# print(anno.getanno(body[2].body[1].body[0], 'definitions_in'))
# breakpoint()
# # Only the argument reaches the expression
# assert len(anno.getanno(body[0], 'definitions_in')) == 1
# while_body = body[1].body
# # x can be either the argument here, or from the previous loop
# assert len(anno.getanno(while_body[0], 'definitions_in')) == 2

# breakpoint()
