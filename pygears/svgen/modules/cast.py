from pygears.typing.uint import IntMeta, UintMeta
from pygears.typing import Union, Tuple, Queue
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svgen import SVGenPlugin
from pygears.svgen.module_base import SVGenGearBase
from pygears.common import cast
from pygears.core.hier_node import HierVisitorBase


class SVGenCast(SVGenGearBase):
    # def channel_ports(self):
    #     super().channel_ports()
    #     t_in = self.ports[0]['type']
    #     t_out = self.ports[1]['type']
    #     iin = self.ports[0]['intf']
    #     iout = self.ports[1]['intf']

    #     if int(t_in) == int(t_out) \
    #        or issubclass(t_out, Union) and issubclass(t_in, Tuple):
    #         self.remove()
    #         iin.implicit = iout.implicit or iin.implicit
    #         for m in iout.consumers.copy():
    #             m[0].connect_intf(m[0].ports[m[1]], iin)

    #             # for p in m.get_intf_ports(iout):
    #             #     m.connect_intf(p, iin)

    def get_module(self, template_env):
        outtype = self.out_ports[0].dtype
        intype = self.in_ports[0].dtype
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


class RemoveEqualReprCastVisitor(HierVisitorBase):
    def SVGenCast(self, svmod):
        super().HierNode(svmod)
        if hasattr(svmod, 'connect'):
            svmod.connect()


def remove_equal_repr_casts(top, conf):
    v = RemoveEqualReprCastVisitor()
    v.visit(top)
    return top


class SVGenSievePlugin(SVGenInstPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][cast] = SVGenCast
        cls.registry['SVGenFlow'] = [svgen_inst, svgen_connect, svgen_generate]
