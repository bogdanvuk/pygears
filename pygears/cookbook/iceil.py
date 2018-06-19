from pygears.typing import Uint
from pygears import gear


@gear(svgen={'svmod_fn': 'iceil.sv'})
def iceil(din: Uint['T'], *, div=4) -> Uint['T']:
    pass
