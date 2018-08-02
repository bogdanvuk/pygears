from pygears import gear, module
from pygears.typing import Queue


@gear(svgen={'svmod_fn': 'project.sv'})
async def project(din: Queue['tdin', 'din_lvl'],
                  *,
                  lvl=1,
                  dout_lvl=b'din_lvl - lvl') -> Queue['tdin', 'dout_lvl']:
    async with din as d:
        yield module().tout(d[:dout_lvl+1])
