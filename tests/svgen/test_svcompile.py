from pygears import gear, Intf, find
from pygears.typing import Integer, Tuple, Uint, Union
from pygears.svgen.svcompile import compile_gear_body
from pygears.util.test_utils import equal_on_nonspace



@gear
async def add(din: Tuple[Integer['N1'], Integer['N2']]) -> b'din[0] + din[1]':
    async with din as data:
        yield data[0] + data[1]


simple_add_res = """always_comb begin
    din.ready <= 1;
    dout.valid <= 0;

    if (din.valid) begin
        din.ready <= dout.ready;
        dout.valid <= 1;
        dout_s <= 11'(din_s.f0) + 11'(din_s.f1);
    end
end"""


def test_simple_add():
    add(Intf(Tuple[Uint[8], Uint[10]]))

    res = compile_gear_body(find('/add'))
    assert equal_on_nonspace(res, simple_add_res)


@gear
async def filt(din: Tuple[Union, Uint]) -> b'din[0]':
    async with din as (d, sel):
        if d.ctrl == sel:
            yield d


simple_filt_res = """always_comb begin
    din.ready <= 1;
    dout.valid <= 0;

    if (din.valid) begin
        if (din_s.f0.ctrl == din_s.f1) begin
            din.ready <= dout.ready;
            dout.valid <= 1;
            dout_s <= din_s.f0;
        end
    end
end
"""


def test_simple_filt():
    filt(Intf(Tuple[Union[Uint[1], Uint[8], Uint[10]], Uint[2]]))

    res = compile_gear_body(find('/filt'))
    assert equal_on_nonspace(res, simple_filt_res)


# from pygears.typing import Queue
# from pygears.cookbook import qcnt
# from pygears.svgen import svgen


# @gear(svgen={'compile': True})
# async def svctest(din: Queue[Uint['T']], *, upper) -> Uint['T']:
#     cnt = Uint[8](0)
#     async for (data, eot) in din:
#         if data > upper * 2:
#             yield data
#             cnt = cnt + 1


# svctest(Intf(Queue[Uint[8]]), upper=2)
# res = compile_gear_body(find('/svctest'))
# print(res)
# svgen('/svctest', outdir='/tools/home/tmp')

# from pygears.sim import sim
# from pygears.cookbook.verif import verif
# from pygears.sim.modules.drv import drv
# from pygears.sim.modules.verilator import SimVerilated
# from pygears.cookbook.delay import delay_rng
# from pygears.sim.extens.vcd import VCD
# from pygears import bind

# seq = [list(range(10))]

# bind('svgen/debug_intfs', ['*'])
# bind('logger/sim/error', lambda x: x)

# report = verif(
#     drv(t=Queue[Uint[8]], seq=seq) | delay_rng(2, 2),
#     f=svctest(sim_cls=SimVerilated, upper=2),
#     ref=svctest(name='ref_model', upper=2),
#     delays=[delay_rng(5, 5)]
#     )

# sim(outdir='/tools/home/tmp', extens=[VCD])

# print(report)
