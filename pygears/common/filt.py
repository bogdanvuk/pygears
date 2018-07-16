from pygears import gear
from pygears.typing import Queue


def filt_type(din, lvl, field_sel):
    return Queue[(din[0].types)[field_sel], lvl]


@gear
def filt(din: Queue['TUnion', 'lvl'],
         *,
         field_sel=0,
         lvl=0,
         w_din=b'int(din[0][0])',
         w_dout=b'int((din[0].types)[field_sel])'
         ) -> b'filt_type(din, lvl, field_sel)':
    pass
