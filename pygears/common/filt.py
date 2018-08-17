from pygears import gear, alternative
from pygears.typing import Queue, Union


def filt_type(din, lvl, sel):
    return Queue[(din[0].types)[sel], lvl]


@gear
def filt(din: Union, *, sel) -> b'din.types[sel]':
    pass


@alternative(filt)
@gear(svgen={'svmod_fn': 'qfilt.sv'})
def qfilt(din: Queue['TUnion', 'lvl'],
          *,
          sel=0,
          filt_lvl=1,
          w_din=b'int(din[0][0])',
          w_dout=b'int((din[0].types)[sel])') -> b'filt_type(din, lvl, sel)':
    pass
