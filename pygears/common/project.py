from pygears import gear
from pygears.typing import Queue


@gear(svgen={'svmod_fn': 'project.sv'})
def project(din: Queue['tdin', 'din_lvl'],
            *,
            lvl=1,
            dout_lvl=b'din_lvl - lvl') -> Queue['tdin', 'dout_lvl']:
    pass
