from pygears import gear, alternative
from pygears import datagear
from pygears.typing import Queue, Union, typeof, Tuple, Uint, Any


def mux_type(dtypes, mapping):
    full_dtypes = tuple(dtypes[mapping[i]] for i in sorted(mapping))
    return Union[full_dtypes]


def full_mapping(dtypes, mapping):
    dout_num = max(mapping.values()) + 1
    fm = mapping.copy()

    for i in range(len(dtypes)):
        if i not in mapping:
            fm[i] = dout_num

    return fm


def dflt_map(dtypes):
    return {i: i for i in range(len(dtypes))}


@gear
async def mux(
        ctrl: Uint,
        *din,
        mapping=b'dflt_map(din)',
        _full_mapping=b'full_mapping(din, mapping)') -> b'mux_type(din, _full_mapping)':

    async with ctrl as c:
        c_map = _full_mapping[int(c)]

        assert c_map < len(din), 'mux: incorrect selection value'
        async with din[c_map] as d:
            yield (d, c)


@gear
async def mux_zip(
        ctrl, *din, mapping=b'dflt_map(din)',
        _full_mapping=b'full_mapping(din, mapping)') -> b'mux_type(din, _full_mapping)':
    async with ctrl as c:
        c_map = _full_mapping[int(c)]

        assert c_map < len(din), 'mux: incorrect selection value'
        async for d in din[c_map]:
            yield (d, c)


@datagear
def field_mux(
        din: Tuple[{
            'ctrl': Uint,
            'data': Any
        }],
        *,
        mapping=b'dflt_map(din["data"])',
        _full_mapping=b'full_mapping(din["data"], mapping)'
) -> b'mux_type(din["data"], _full_mapping)':
    c_map = _full_mapping[int(din['ctrl'])]
    return (din['data'][c_map], c_map)
