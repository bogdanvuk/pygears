from pygears import gear, module
from pygears.typing import Integer, Uint
from pygears.core.intf import IntfOperPlugin


@gear
async def shr(din: Integer,
              cfg: Uint['w_shamt'],
              *,
              signed=b'typeof(din, Int)') -> b'din':

    async with cfg as shamt:
        async with din as d:
            yield module().tout(d >> shamt)


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__rshift__'] = shr
