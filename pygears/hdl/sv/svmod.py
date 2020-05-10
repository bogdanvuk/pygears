from pygears import reg
from pygears.hdl.modinst import HDLModuleInst
from .sv_keywords import sv_keywords
from collections import OrderedDict
from pygears.conf import inject, Inject


class SVModuleInst(HDLModuleInst):
    @inject
    def __init__(self, node):
        super().__init__(node)
        self.hdlgen_map = reg[f"{self.lang}gen/map"]

    @property
    def inst_name(self):
        inst_name = super().inst_name

        if inst_name in sv_keywords:
            return f'{inst_name}_i'
        else:
            return inst_name

    def get_impl_wrap(self, template_env):
        intfs = template_env.port_intfs(self.node)

        port_map = {}
        for i in intfs:
            name = i['name']
            port_map[f'{name}_data'] = f'{name}.data'
            port_map[f'{name}_valid'] = f'{name}.valid'
            port_map[f'{name}_ready'] = f'{name}.ready'

        context = {
            'wrap_module_name': self.module_name,
            'module_name': self.module_basename,
            'inst_name': f'{self.module_basename}_i',
            'intfs': intfs,
            'sigs': self.node.params['signals'],
            'param_map': self.params,
            'port_map': port_map
        }

        return template_env.render_local(__file__, "impl_wrap.j2", context)

    def get_synth_wrap(self, template_env):
        context = {
            'wrap_module_name': f'wrap_{self.module_name}',
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'intfs': template_env.port_intfs(self.node),
            'sigs': self.node.params['signals'],
            'param_map': self.resolver.params
        }

        return template_env.render('.', "module_synth_wrap.j2", context)

    def get_out_port_map_intf_name(self, port):
        basename = self.hdlgen_map[port.consumer].basename
        if self.lang == 'sv':
            return basename
        else:
            return basename, None, None

    def get_in_port_map_intf_name(self, port):
        intf = port.producer
        hdlgen_intf = self.hdlgen_map[intf]

        if len(intf.consumers) == 1:
            if self.lang == 'sv':
                return hdlgen_intf.outname
            else:
                return hdlgen_intf.outname, None, None
        else:
            i = intf.consumers.index(port)
            if self.lang == 'sv':
                return f'{hdlgen_intf.outname}[{i}]'
            else:
                return (hdlgen_intf.outname, i, int(intf.dtype))

    def get_inst(self, template_env, port_map=None):
        if not port_map:
            in_port_map = [(port.basename,
                            self.get_in_port_map_intf_name(port))
                           for port in self.node.in_ports]

            out_port_map = [(port.basename,
                             self.get_out_port_map_intf_name(port))
                            for port in self.node.out_ports]
            port_map = OrderedDict(in_port_map + out_port_map)

        sigmap = {}
        for s in self.node.params['signals']:
            sigmap[s.name] = self.node.params['sigmap'].get(s.name, s.name)

        context = {
            'rst_name': 'rst',
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'param_map': self.params,
            'port_map': port_map,
            'sig_map': sigmap
        }

        return template_env.snippets.module_inst(**context)
