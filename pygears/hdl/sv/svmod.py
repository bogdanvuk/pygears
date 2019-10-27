import fnmatch
import functools
import os
from collections import OrderedDict

from pygears import registry, safe_bind
from pygears.core.gear import OutSig
from .inst import SVGenInstPlugin
from .svparse import parse
from pygears.hdl.modinst import HDLModuleInst

from .svcompile import compile_gear
from .inst import svgen_log
from .sv_keywords import sv_keywords


class SVModuleInst(HDLModuleInst):
    def __init__(self, node):
        super().__init__(node, 'sv')
        self.svgen_map = registry("svgen/map")

    @property
    def inst_name(self):
        inst_name = super().inst_name

        if inst_name in sv_keywords:
            return f'{inst_name}_i'
        else:
            return inst_name

    @property
    @functools.lru_cache()
    def traced(self):
        self_traced = any(
            fnmatch.fnmatch(self.node.name, p)
            for p in registry('debug/trace'))

        if self.is_hierarchical:
            children_traced = any(self.svgen_map[child].traced
                                  for child in self.node.child)
        else:
            children_traced = False

        return self_traced or children_traced

    @property
    def non_sv_impl(self):
        if not super().impl_path:
            return False

        splitext = os.path.splitext(super().impl_path)
        if not splitext or not splitext[1]:
            return False

        return splitext[1] != '.sv'

    def get_module(self, template_env):
        if self.non_sv_impl:
            return self.get_impl_wrap(template_env)
        else:
            return super().get_module(template_env)

    @property
    def module_name(self):
        module_name = super().module_name

        if self.non_sv_impl:
            return f'{module_name}_sv'

        return module_name

    @property
    def impl_path(self):
        if self.non_sv_impl:
            return None
        else:
            return super().impl_path

    @property
    def files(self):
        if self.non_sv_impl:
            return super().files + [super().impl_path]
        else:
            return super().files

    @property
    def file_name(self):
        if self.non_sv_impl:
            return f'{self.module_name}.sv'
        else:
            return super().file_name

    def get_impl_wrap(self, template_env):
        intfs = list(self.port_configs)

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
            'intfs': list(self.port_configs),
            'sigs': self.node.params['signals'],
            'param_map': self.params,
            'port_map': port_map
        }

        return template_env.render_local(__file__, "impl_wrap.j2", context)

    @property
    def is_generated(self):
        return super().is_generated or self.non_sv_impl

    @functools.lru_cache()
    def impl_parse(self):
        if self.impl_path:
            with open(self.impl_path, 'r') as f:
                return parse(f.read())

        if self.non_sv_impl:
            return None

        svgen_log().warning(
            f'SystemVerilog file not found for {self.node.name}')

    def get_synth_wrap(self, template_env):
        context = {
            'wrap_module_name': f'wrap_{self.module_name}',
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'intfs': list(self.port_configs),
            'sigs': self.node.params['signals'],
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

    def get_compiled_module(self, template_env):
        return compile_gear(self.node.gear, template_env, self.module_context)

    def get_hier_module(self, template_env):
        context = self.module_context

        self.svgen_map = registry('svgen/map')

        for child in self.node.local_interfaces():
            svgen = self.svgen_map[child]
            contents = svgen.get_inst(template_env)
            if contents:
                context['inst'].append(contents)

        for child in self.node.local_modules():
            for s in child.params['signals']:
                if isinstance(s, OutSig):
                    name = child.params['sigmap'][s.name]
                    context['inst'].append(f'logic [{s.width-1}:0] {name};')

            svgen = self.svgen_map[child]
            if hasattr(svgen, 'get_inst'):
                contents = svgen.get_inst(template_env)
                if contents:
                    if svgen.traced:
                        context['inst'].append('/*verilator tracing_on*/')
                    context['inst'].append(contents)
                    if svgen.traced:
                        context['inst'].append('/*verilator tracing_off*/')

        return template_env.render_local(__file__, "hier_module.j2", context)

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
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'param_map': param_map,
            'port_map': OrderedDict(in_port_map + out_port_map),
            'sig_map': self.node.params['sigmap']
        }

        return template_env.snippets.module_inst(**context)
