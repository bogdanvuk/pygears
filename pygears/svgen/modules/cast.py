from pygears.typing.uint import IntMeta, UintMeta
from pygears.typing import Queue
from pygears.svgen.svgen import SVGenPlugin
from pygears.svgen.util import svgen_visitor
from pygears.rtl.connect import rtl_connect
from pygears.rtl.inst import RTLNodeInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.common.cast import cast
from pygears.rtl.gear import RTLGearHierVisitor


class SVGenCast(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        outtype = self.node.out_ports[0].dtype
        intype = self.node.in_ports[0].dtype
        out_width = int(outtype)

        if isinstance(outtype, IntMeta):
            if isinstance(intype, UintMeta):
                data_expr = f"{out_width}'(din.data)"
            else:
                data_expr = f"{out_width}'(signed'(din.data))"
        elif issubclass(outtype, Queue) and outtype[0] == intype:
            if (int(intype) != 0):
                data_expr = "{1'b1, din.data}"
            else:
                data_expr = "1"
        else:
            data_expr = f"{out_width}'(din.data)"

        context = {
            'data_expr': data_expr,
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "cast.j2", context)


@svgen_visitor
class RemoveEqualReprCastVisitor(RTLGearHierVisitor):
    def cast(self, node):
        pout = node.out_ports[0]
        pin = node.in_ports[0]

        if int(pin.dtype) == int(pout.dtype):
            node.bypass()


class SVGenSievePlugin(RTLNodeInstPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][cast] = SVGenCast
        cls.registry['SVGenFlow'].insert(
            cls.registry['SVGenFlow'].index(rtl_connect) + 1,
            RemoveEqualReprCastVisitor)
