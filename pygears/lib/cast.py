from pygears import gear
from pygears.typing import cast as type_cast
from pygears.typing import trunc as type_trunc
from pygears.conf import reg
from pygears.core.intf import IntfOperPlugin
from pygears.hdl.util import HDLGearHierVisitor, flow_visitor
from pygears.hdl.sv import SVGenPlugin
from pygears.hdl.v import VGenPlugin


@gear
async def trunc(din, *, t) -> b'type_trunc(din, t)':
    async with din as d:
        yield type_trunc(d, t)


@gear
async def cast(din, *, t) -> b'type_cast(din, t)':
    async with din as d:
        yield type_cast(d, t)


def pipe(self, other):
    if self.producer is not None:
        name = f'cast_{self.producer.basename}'
    else:
        name = 'cast'

    return cast(self, t=other, name=name)


@flow_visitor
class RemoveEqualReprCastVisitor(HDLGearHierVisitor):
    def cast(self, node):
        pout = node.out_ports[0]
        pin = node.in_ports[0]

        if pin.dtype.width == pout.dtype.width:
            node.bypass()


class HDLCastPlugin(IntfOperPlugin, VGenPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        reg['gear/intf_oper/__or__'] = pipe
        reg['vgen/flow'].insert(0, RemoveEqualReprCastVisitor)
        reg['svgen/flow'].insert(0, RemoveEqualReprCastVisitor)
