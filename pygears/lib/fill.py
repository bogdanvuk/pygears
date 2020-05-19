from pygears import gear, reg
from pygears.typing import Union
from pygears.lib.demux import demux_ctrl
from pygears.lib.mux import mux
from pygears.lib.shred import shred


def fill_type(din_t, union_t, sel):
    dtypes = list(union_t.types).copy()
    dtypes[sel] = din_t

    return Union[tuple(dtypes)]


@gear
def fill(din,
         union_din: Union,
         *,
         fdemux=demux_ctrl,
         fmux=mux,
         sel) -> b'fill_type(din, union_din, sel)':
    fields = union_din | fdemux
    fields_list = list(fields)

    fields_list[sel+1] | shred

    fields_list[sel+1] = din
    return tuple(fields_list) | fmux
