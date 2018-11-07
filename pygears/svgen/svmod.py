import os
import functools
from collections import OrderedDict

import pygears
from pygears import registry, safe_bind
from pygears.definitions import COMMON_SVLIB_DIR, COOKBOOK_SVLIB_DIR
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svparse import parse

from .svtranspile import transpile_gear
from .inst import svgen_log


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
        self.svgen_map = registry("svgen/map")

    @property
    @functools.lru_cache()
    def sv_template_path(self):
        return find_in_dirs(self.sv_module_basename + '.svt',
                            registry('svgen/sv_paths'))

    @property
    @functools.lru_cache()
    def sv_impl_path(self):
        if not self.is_generated:
            return find_in_dirs(self.sv_module_base_path,
                                registry('svgen/sv_paths'))
        else:
            return None

    @property
    def is_transpiled(self):
        return self.node.params.get('svgen', {}).get('transpile', False)

    @property
    def is_generated(self):
        return getattr(self.node, 'gear', None) in registry('svgen/module_namespace') \
            or self.is_transpiled \
            or self.sv_template_path \
            or self.is_hierarchical

    @property
    def is_hierarchical(self):
        return self.node.is_hierarchical

    @property
    def sv_module_basename(self):
        if hasattr(self.node, 'gear'):
            return self.node.gear.definition.__name__
        else:
            return self.node.name

    @property
    def sv_module_base_path(self):
        svgen_params = self.node.params.get('svgen', {})
        return svgen_params.get('svmod_fn', self.sv_module_basename + ".sv")

    @property
    def sv_module_name(self):
        if self.is_hierarchical:
            # if there is a module with the same name as this hierarchical
            # module, append "_hier" to disambiguate
            if find_in_dirs(self.hier_sv_path_name + '.sv',
                            registry('svgen/sv_paths')):
                return self.hier_sv_path_name + '_hier'
            else:
                return self.hier_sv_path_name
        elif self.is_generated:
            return self.hier_sv_path_name
        else:
            return self.sv_impl_module_name

    @property
    def sv_inst_name(self):
        return f'{self.node.basename}_i'

    @property
    def sv_file_name(self):
        svgen_params = self.node.params.get('svgen', {})
        return svgen_params.get('svmod_fn', self.sv_module_name + ".sv")

    @functools.lru_cache()
    def sv_impl_parse(self):
        if self.sv_impl_path:
            with open(self.sv_impl_path, 'r') as f:
                return parse(f.read())
        else:
            svgen_log().warning(
                f'SystemVerilog file not found for {self.node.name}')

    @property
    @functools.lru_cache()
    def sv_impl_module_name(self):
        parse_res = self.sv_impl_parse()
        if parse_res:
            return parse_res[0]
        else:
            return self.sv_module_basename

    @property
    def sv_params(self):
        parse_res = self.sv_impl_parse()
        if parse_res:
            return parse_res[-1]
        else:
            return {}

    @property
    def params(self):
        if not self.is_generated:
            return {
                k.upper(): int(v)
                for k, v in self.node.params.items()
                if (k.upper() in self.sv_params) and (
                    int(v) != int(self.sv_params[k.upper()]['val']))
            }
        else:
            return {}

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
        if not self.is_generated:
            return None

        context = {
            'pygears': pygears,
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'params': self.node.params,
            'inst': [],
            'generics': [],
            'has_local_rst': self.has_local_rst
        }

        for port in context['intfs']:
            context[f'_{port["name"]}'] = port
            context[f'_{port["name"]}_t'] = port['type']

        if self.is_hierarchical:
            self.svgen_map = registry('svgen/map')

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
        elif self.sv_template_path:

            for intf in context['intfs']:
                context[intf['name']] = intf

            return template_env.render_local(
                self.sv_template_path, os.path.basename(self.sv_template_path),
                context)

        elif self.is_transpiled:
            return transpile_gear(self.node.gear, template_env, context)
        else:
            svgen_log().warning(
                f'No method for generating the gear {self.node.name}')
            return None

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
        safe_bind('svgen/module_namespace/Gear', SVModuleGen)
        safe_bind('svgen/module_namespace/RTLNodeDesign', SVTopGen)

        if 'sv_paths' not in cls.registry['svgen']:
            cls.registry['svgen']['sv_paths'] = []
        cls.registry['svgen']['sv_paths'].extend(
            [COMMON_SVLIB_DIR, COOKBOOK_SVLIB_DIR])
