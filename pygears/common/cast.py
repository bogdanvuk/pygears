from pygears import gear, module
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Int, Queue, Tuple, Uint, Union
from pygears.typing.base import typeof
from pygears.typing_common.codec import code, decode


@gear
async def cast(din, *, cast_type) -> b'cast(din, cast_type)':
    async with din as d:
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
    if self.producer is not None:
        name = f'cast_{self.producer.basename}'
    else:
        name = 'cast'

    return cast(self, cast_type=other, name=name)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__or__', pipe)
