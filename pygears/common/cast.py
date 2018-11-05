from pygears import gear, module
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Int, Queue, Tuple, Uint, Union, Integer
from pygears.typing.base import typeof
from pygears.typing_common.codec import code, decode
from pygears.rtl.connect import rtl_connect
from pygears.rtl.inst import RTLNodeInstPlugin
from pygears.typing_common import cast as type_cast
from pygears.rtl.gear import RTLGearHierVisitor
from pygears.svgen.svgen import SVGenPlugin
from pygears.svgen.util import svgen_visitor


@gear
async def cast(din, *, cast_type) -> b'type_cast(din, cast_type)':
    async with din as d:
        if typeof(cast_type,
                  Int) and (not cast_type.is_specified()) and typeof(
                      din.dtype, (Uint, Int)):
            dout = module().tout(d)
        elif typeof(module().tout, Integer) and typeof(din.dtype, Integer):
            tout_range = (1 << int(module().tout))
            val = int(d) & (tout_range - 1)

            if typeof(module().tout, Int):
                max_uint = tout_range / 2 - 1
                if val > max_uint:
                    val -= tout_range

            dout = module().tout(val)
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


@svgen_visitor
class RemoveEqualReprCastVisitor(RTLGearHierVisitor):
    def cast(self, node):
        pout = node.out_ports[0]
        pin = node.in_ports[0]

        print(f'Equal repr: {node.name}')
        if int(pin.dtype) == int(pout.dtype):
            node.bypass()


class PipeIntfOperPlugin(IntfOperPlugin, RTLNodeInstPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__or__', pipe)
        cls.registry['svgen']['flow'].insert(
            cls.registry['svgen']['flow'].index(rtl_connect) + 1,
            RemoveEqualReprCastVisitor)
