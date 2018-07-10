from pygears import gear, registry
from pygears.typing import Union
from pygears.common.demux import demux
from pygears.common.mux import mux
from pygears.common.shred import shred


def fill_type(din_t, union_t, field_sel):
    dtypes = union_t.types.copy()
    dtypes[field_sel] = din_t

    return Union[tuple(dtypes)]


@gear
def fill(din,
         union_din: Union,
         *,
         fmux=mux,
         field_sel) -> b'fill_type(din, union_din, field_sel)':
    fields = union_din | demux(ctrl_out=True)
    fields_list = list(fields)

    fields_list[field_sel+1] | shred

    fields_list[field_sel+1] = din
    return tuple(fields_list) | fmux
