from pygears import module, Intf, gear, registry
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.sim.modules import SimVerilated
from pygears.typing import Uint, Tuple
from pygears.lib import add, fmap, decouple
from functools import partial

# from pygears.sim import delta, sim
# from pygears.typing import Uint
# from pygears.lib.verif import drv
# from pygears.lib import shred

# @gear
# async def multicycle(*din) -> b'din':
#     phase = 'forward'
#     output = set()

#     while (1):
#         import pdb; pdb.set_trace()
#         if phase == 'forward':
#             for i, (inp, outp) in enumerate(zip(din, module().dout)):
#                 if outp.ready_nb() and (not inp.empty()):
#                     outp.put_nb(inp.pull_nb())
#                     output.add(i)
#         else:
#             for i in output:
#                 if module().dout[i].ready_nb():
#                     din[i].ack()

#         phase = await delta()


@gear
def dualcycle(din0, din1) -> (b'din0[0]', b'din1[0]'):
    return din0[0], din1[0]


@gear
def dualcycle_wrap_thin(din) -> b'din[0][0]':
    middle = Intf(din.dtype[0])

    return dualcycle(din,
                     middle,
                     intfs={'dout0': middle},
                     sim_cls=partial(SimVerilated, timeout=1))


@gear
def dualcycle_wrap_comb_middle(din) -> b'din[0][0]':
    middle = Intf(din.dtype[0])

    middle_back = middle | fmap(f=(add(0), add(0)))

    return dualcycle(din,
                     middle_back,
                     intfs={'dout0': middle},
                     sim_cls=partial(SimVerilated, timeout=1))


@gear
def dualcycle_wrap_decouple_middle(din) -> b'din[0][0]':
    middle = Intf(din.dtype[0])

    middle_back = middle | decouple

    return dualcycle(din,
                     middle_back,
                     intfs={'dout0': middle},
                     sim_cls=partial(SimVerilated, timeout=1))


def multicycle_test_gen(tmpdir, func, latency):
    data_num = 10

    data = [((i, 1), 2) for i in range(data_num)]

    directed(drv(t=Tuple[Tuple[Uint[8], Uint[8]], Uint[8]], seq=data),
             f=func,
             ref=list(range(data_num)))

    sim(outdir=tmpdir)

    assert registry('sim/timestep') == (data_num + latency - 1)


def test_multicycle_thin(tmpdir):
    # One additional cycle is needed for Verilator timeout set above
    multicycle_test_gen(tmpdir, dualcycle_wrap_thin, latency=2)


def test_multicycle_comb_middle(tmpdir):
    # One additional cycle is needed for Verilator timeout set above
    multicycle_test_gen(tmpdir, dualcycle_wrap_comb_middle, latency=2)


def test_multicycle_decouple_middle(tmpdir):
    # One additional cycle is needed for Verilator timeout set above
    multicycle_test_gen(tmpdir, dualcycle_wrap_decouple_middle, latency=4)
