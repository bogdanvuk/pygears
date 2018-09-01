from collections import OrderedDict

from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svparse import parse
from pygears.definitions import COMMON_SVLIB_DIR, COOKBOOK_SVLIB_DIR
from pygears import registry

import os


def find_in_dirs(fn, dirs):
    for d in dirs:
        full_path = os.path.join(d, fn)
        if os.path.exists(full_path):
            return full_path
    else:
        return None


class SVModuleGen:
    def __init__(self, node):
        self.node = node
        self.svgen_map = registry("SVGenMap")
        self._sv_module_name = None
        self.sv_module_path = None
        self.sv_params = {}

        if not self.is_generated:
            try:
                self.sv_module_path, self._sv_module_name, self.sv_params = self.get_sv_module_info(
                )
            except FileNotFoundError:
                print(
                    f'Warning: SystemVerilog file not found for {self.node.name}'
                )
        elif self.is_hierarchical:
            if find_in_dirs(self.sv_file_name,
                            registry('SVGenSystemVerilogPaths')):
                self.sv_module_path = None
                self._sv_module_name = self.hier_sv_path_name + '_hier'

    @property
    def is_generated(self):
        return self.is_hierarchical

    @property
    def is_hierarchical(self):
        return self.node.is_hierarchical

    @property
    def sv_module_name(self):
        if self.is_generated:
            return self._sv_module_name or self.hier_sv_path_name
        else:
            return self._sv_module_name or self.node.gear.definition.__name__

    @property
    def sv_inst_name(self):
        return f'{self.node.basename}_i'

    @property
    def sv_file_name(self):
        svgen_params = self.node.params.get('svgen', {})
        return svgen_params.get('svmod_fn', self.sv_module_name + ".sv")

    def get_sv_module_info(self):
        svmod_fn = self.sv_file_name
        if svmod_fn:
            svmod_path = find_in_dirs(svmod_fn,
                                      registry('SVGenSystemVerilogPaths'))
            if svmod_path:
                with open(svmod_path, 'r') as f:
                    name, _, _, svparams = parse(f.read())

                return svmod_path, name, svparams

        raise FileNotFoundError(
            f'SystemVerilog file not found for {self.node.name}')

    @property
    def params(self):
        return {
            k.upper(): int(v)
            for k, v in self.node.params.items()
            if (k.upper() in self.sv_params) and (
                int(v) != int(self.sv_params[k.upper()]['val']))
        }

    def sv_port_configs(self):
        for p in self.node.in_ports:
            yield self.get_sv_port_config(
                'consumer', type_=p.dtype, name=p.basename)

        for p in self.node.out_ports:
            yield self.get_sv_port_config(
                'producer', type_=p.dtype, name=p.basename)

    def get_sv_port_config(self, modport, type_, name):
        return {
            'modport': modport,
            'name': name,
            'type': type_,
            'width': int(type_),
            'local_type': type_
        }

    def get_synth_wrap(self, template_env):

        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'param_map': self.params
        }
        return template_env.render_local(__file__, "module_synth_wrap.j2",
                                         context)

    def get_out_port_map_intf_name(self, port):
        return self.svgen_map[port.consumer].basename

    def get_in_port_map_intf_name(self, port):
        intf = port.producer
        svgen_intf = self.svgen_map[intf]

        if len(intf.consumers) == 1:
            return svgen_intf.outname
        else:
            i = intf.consumers.index(port)
            return f'{svgen_intf.outname}[{i}]'

    @property
    def has_local_rst(self):
        return any(child.gear.definition.__name__ == 'local_rst'
                   for child in self.node.local_modules())

    @property
    def hier_sv_path_name(self):
        trimmed_name = self.node.name

        if trimmed_name.startswith('/'):
            trimmed_name = trimmed_name[1:]

        return trimmed_name.replace('/', '_')

    def get_module(self, template_env):
        if self.is_hierarchical:
            self.svgen_map = registry('SVGenMap')

            context = {
                'module_name': self.sv_module_name,
                'generics': [],
                'intfs': list(self.sv_port_configs()),
                'inst': [],
                'has_local_rst': self.has_local_rst
            }

            for child in self.node.local_interfaces():
                svgen = self.svgen_map[child]
                contents = svgen.get_inst(template_env)
                if contents:
                    context['inst'].append(contents)

            for child in self.node.local_modules():
                svgen = self.svgen_map[child]
                if hasattr(svgen, 'get_inst'):
                    contents = svgen.get_inst(template_env)
                    if contents:
                        context['inst'].append(contents)

            return template_env.render_local(__file__, "hier_module.j2",
                                             context)

    def update_port_name(self, port, name):
        port['name'] = name

    def get_inst(self, template_env):
        param_map = self.params

        in_port_map = [(port.basename, self.get_in_port_map_intf_name(port))
                       for port in self.node.in_ports]

        out_port_map = [(port.basename, self.get_out_port_map_intf_name(port))
                        for port in self.node.out_ports]

        rst_name = 'local_rst' if self.svgen_map[
            self.node.parent].has_local_rst else 'rst'

        try:
            if self.node.out_ports[-1].basename == 'rst_o':
                rst_name = 'rst'
        except:
            pass

        context = {
            'rst_name': rst_name,
            'module_name': self.sv_module_name,
            'inst_name': self.sv_inst_name,
            'param_map': param_map,
            'port_map': OrderedDict(in_port_map + out_port_map)
        }

        return template_env.snippets.module_inst(**context)


class SVTopGen(SVModuleGen):
    @property
    def sv_module_name(self):
        return "top"


class SVGenSVModPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Gear'] = SVModuleGen
        cls.registry['SVGenModuleNamespace']['RTLNodeDesign'] = SVTopGen

        cls.registry['SVGenSystemVerilogPaths'].extend(
            [COMMON_SVLIB_DIR, COOKBOOK_SVLIB_DIR])
