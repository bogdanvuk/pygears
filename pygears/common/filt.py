from pygears import gear
from pygears.typing import Queue


@gear
def filt(din: Queue['TUnion', 'lvl'],
         *,
         field_sel=0,
         lvl=0,
         w_din=b'int(din[0][0])'
         ) -> Queue['(din[0].types)[field_sel]', 'lvl']:
    pass
