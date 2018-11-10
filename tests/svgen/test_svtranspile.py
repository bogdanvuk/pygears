from pygears import gear, Intf, find
from pygears.typing import Integer, Tuple, Uint
from pygears.svgen.svtranspile import transpile_gear_body


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

    res = transpile_gear_body(find('/add'))
    assert res == simple_add_res
