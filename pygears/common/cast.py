from pygears import gear, module
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.rtl.connect import rtl_connect
from pygears.rtl.inst import RTLNodeInstPlugin
from pygears.typing_common import cast as type_cast
from pygears.rtl.gear import RTLGearHierVisitor
from pygears.svgen.svgen import SVGenPlugin
from pygears.rtl import flow_visitor


@gear
async def cast(din, *, cast_type) -> b'type_cast(din, cast_type)':
    async with din as d:
        yield type_cast(d, module().tout)


def pipe(self, other):
    if self.producer is not None:
        name = f'cast_{self.producer.basename}'
    else:
        name = 'cast'

    return cast(self, cast_type=other, name=name)


@flow_visitor
class RemoveEqualReprCastVisitor(RTLGearHierVisitor):
    def cast(self, node):
        pout = node.out_ports[0]
        pin = node.in_ports[0]

        if int(pin.dtype) == int(pout.dtype):
            node.bypass()


class PipeIntfOperPlugin(IntfOperPlugin, RTLNodeInstPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__or__', pipe)
        cls.registry['svgen']['flow'].insert(
            cls.registry['svgen']['flow'].index(rtl_connect) + 1,
            RemoveEqualReprCastVisitor)
