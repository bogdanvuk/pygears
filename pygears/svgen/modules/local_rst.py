from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.common.local_rst import local_rst


class SVGenLocalRst(SVModuleGen):
    def get_inst(self, template_env):
        in_intf_name = self.get_in_port_map_intf_name(self.node.in_ports[0])

        return f"""local_rst local_rst_i (
    .clk(clk),
    .rst(rst),
    .local_rst(local_rst),
    .din({in_intf_name})
);
"""


class SVGenAlignPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][local_rst] = SVGenLocalRst
