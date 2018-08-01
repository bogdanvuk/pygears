from pygears import module, gear
from pygears.typing.base import TypingMeta, typeof
from pygears.core.intf import IntfOperPlugin
from pygears.typing_common.codec import code, decode
from pygears.typing import Int, Tuple, Queue, Uint, Union


@gear
async def cast(din, *, cast_type) -> b'cast(din, cast_type)':
    async with din as d:
        # if module().name == '/rd_addrgen/fmap1/cast_dout':
        #     import pdb; pdb.set_trace()

        if typeof(cast_type,
                  Int) and (not cast_type.is_specified()) and typeof(
                      din.dtype, (Uint, Int)):
            dout = module().tout(d)
        elif typeof(cast_type, Tuple) and typeof(
                din.dtype, Queue) and not cast_type.is_specified():
            dout = module().tout((d[0], d[1:]))
        elif (typeof(cast_type, Union) and typeof(din.dtype, Tuple)
              and len(din.dtype) == 2 and not cast_type.is_specified()):
            pass
        else:
            dout = decode(module().tout, code(din.dtype, d))

        yield dout


def pipe(self, other):
    if isinstance(other, (str, TypingMeta)):
        if self.producer is not None:
            name = f'cast_{self.producer.basename}'
        else:
            name = 'cast'

        return cast(self, cast_type=other, name=name)
    else:
        return other.__ror__(self)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe
