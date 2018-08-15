from pygears import gear, registry
from pygears.typing import Union
from pygears.common.demux import demux
from pygears.common.mux import mux
from pygears.common.shred import shred


def fill_type(din_t, union_t, sel):
    dtypes = union_t.types.copy()
    dtypes[sel] = din_t

    return Union[tuple(dtypes)]


@gear
def fill(din,
         union_din: Union,
         *,
         fdemux=demux(ctrl_out=True),
         fmux=mux,
         sel) -> b'fill_type(din, union_din, sel)':
    fields = union_din | fdemux
    fields_list = list(fields)

    fields_list[sel+1] | shred

    fields_list[sel+1] = din
    return tuple(fields_list) | fmux
