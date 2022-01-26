from pygears import reg
from pygears.hdl.modinst import HDLModuleInst
from .sv_keywords import sv_keywords
from collections import OrderedDict
from pygears.conf import inject, Inject
from pygears.hdl import hdlmod, mod_lang, rename_ambiguous


class SVModuleInst(HDLModuleInst):
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
            'sigs': self.node.meta_kwds['signals'],
            'param_map': self.params,
            'port_map': port_map
        }

        return template_env.render_local(__file__, "impl_wrap.j2", context)

    def get_wrap_portmap(self, parent_lang):
        sig_map = {}
        for s in self.node.meta_kwds['signals']:
            sig_map[s.name] = s.name

        port_map = {}
        for p in self.node.in_ports + self.node.out_ports:
            name = p.basename
            if self.lang == 'sv':
                port_map[name] = name
            elif parent_lang == 'sv':
                sig_map[f'{name}_valid'] = f'{name}.valid'
                sig_map[f'{name}_ready'] = f'{name}.ready'
                sig_map[f'{name}_data'] = f'{name}.data'
            else:
                port_map[name] = name

        return port_map, sig_map

    def get_wrap(self, parent_lang):
        template_env = reg[f'{parent_lang}gen/templenv']

        port_map, sigmap = self.get_wrap_portmap(parent_lang)

        context = {
            'rst_name': 'rst',
            'wrap_module_name': self.wrap_module_name,
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'param_map': self.params,
            'port_map': port_map,
            'intfs': template_env.port_intfs(self.node),
            'sigs': self.node.meta_kwds['signals'],
            'sig_map': sigmap
        }

        return template_env.render(template_env.basedir, f"{self.lang}_wrap.j2", context)

    def get_synth_wrap(self, template_env):
        context = {
            'wrap_module_name': f'wrap_{self.module_name}',
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'intfs': template_env.port_intfs(self.node),
            'sigs': self.node.meta_kwds.get('signals', {}),
            'param_map': self.resolver.params
        }

        return template_env.render('.', "module_synth_wrap.j2", context)

    def get_out_port_map_intf_name(self, port, lang):
        basename = hdlmod(port.consumer).basename
        if lang == 'sv':
            return basename
        else:
            return basename, None

    def get_in_port_map_intf_name(self, port, lang):
        intf = port.producer
        hdlgen_intf = hdlmod(intf)

        if len(intf.consumers) == 1:
            if lang == 'sv':
                return hdlgen_intf.outname
            else:
                return hdlgen_intf.outname, None
        else:
            i = intf.consumers.index(port)
            if lang == 'sv':
                return f'{hdlgen_intf.outname}[{i}]'
            else:
                return (hdlgen_intf.outname, i)

    def get_inst(self, template_env, port_map=None):
        parent_lang = mod_lang(self.node.parent)
        module_name = self.wrap_module_name

        if parent_lang == self.lang:
            params = self.params
        else:
            template_env = reg[f'{parent_lang}gen/templenv']
            params = {}

        if not port_map:
            in_port_map = [(port.basename,
                            self.get_in_port_map_intf_name(port, parent_lang))
                           for port in self.node.in_ports]

            out_port_map = [(port.basename,
                             self.get_out_port_map_intf_name(port, parent_lang))
                            for port in self.node.out_ports]
            port_map = OrderedDict(in_port_map + out_port_map)

        sigmap = {}
        for s in self.node.meta_kwds['signals']:
            sigmap[s.name] = self.node.params['sigmap'].get(s.name, s.name)

        context = {
            'rst_name': 'rst',
            'module_name': rename_ambiguous(module_name, self.lang),
            'inst_name': self.inst_name,
            'param_map': params,
            'port_map': port_map,
            'sig_map': sigmap
        }

        return template_env.snippets.module_inst(**context)
