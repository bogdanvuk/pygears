from pygears import gear, Intf, find
from pygears.typing import Integer, Tuple, Uint, Union
from pygears.svgen.svcompile import compile_gear_body


@gear
async def add(din: Tuple[Integer['N1'], Integer['N2']]) -> b'din[0] + din[1]':
    async with din as data:
        yield data[0] + data[1]


simple_add_res = """if (din.valid) begin
    din.ready = dout.ready;
    dout.valid = 1;
    dout_s = 11'(din_s.f0) + 11'(din_s.f1);
end"""


def test_simple_add():
    add(Intf(Tuple[Uint[8], Uint[10]]))

    res = compile_gear_body(find('/add'))
    assert res == simple_add_res


@gear
async def filt(din: Tuple[Union, Uint]) -> b'din[0]':
    async with din as (d, sel):
        if d.ctrl == sel:
            yield d


simple_filt_res = """if (din.valid) begin
    if (din_s.f0.ctrl == din_s.f1) begin
        din.ready = dout.ready;
        dout.valid = 1;
        dout_s = din_s.f0;
    end
end"""


def test_simple_filt():
    filt(Intf(Tuple[Union[Uint[1], Uint[8], Uint[10]], Uint[2]]))

    res = compile_gear_body(find('/filt'))
    assert res == simple_filt_res


# from pygears.typing import Queue

# @gear
# async def qcnt_test(din: Queue, *, lvl=1, w_out=16) -> Queue[Uint['w_out']]:
#     cnt = 0
#     async for (data, *eot) in din:
#         if all(eot[:din.dtype.lvl - lvl]):
#             yield (cnt, all(eot))
#             cnt += 1


# qcnt_test(Intf(Queue[Uint[2]]))
# res = compile_gear_body(find('/qcnt_test'))
# print(res)
