from pygears import gear
from pygears.typing import Queue, Union, typeof

from .union import union_collapse


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


# @gear(svgen={'compile': True, 'inline_conditions': True})
@gear
async def mux(ctrl,
              *din,
              mapping=b'dflt_map(din)',
              _full_mapping=b'full_mapping(din, mapping)'
              ) -> b'mux_type(din, _full_mapping)':
    async with ctrl as c:
        c_map = _full_mapping[c]

        assert c_map < len(din), 'mux: incorrect selection value'
        if typeof(din[0].dtype, Queue):
            async for d in din[c_map]:
                yield (d, c)
        else:
            async with din[c_map] as d:
                yield (d, c)


@gear
def mux_zip(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_valve(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_by(ctrl, *din, fmux=mux):
    return fmux(ctrl, *din) | union_collapse
