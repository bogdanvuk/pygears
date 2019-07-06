import fnmatch
import functools
from collections import OrderedDict

from pygears import registry, safe_bind
from pygears.core.gear import OutSig
from .inst import SVGenInstPlugin
from .svparse import parse
from pygears.hdl.modinst import HDLModuleInst

from .svcompile import compile_gear
from .inst import svgen_log
from .sv_keywords import sv_keywords


class SVModuleGen(HDLModuleInst):
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
            for p in registry('hdl/debug_intfs'))

        if self.is_hierarchical:
            children_traced = any(self.svgen_map[child].traced
                                  for child in self.node.child)
        else:
            children_traced = False

        return self_traced or children_traced

    @functools.lru_cache()
    def impl_parse(self):
        if self.impl_path:
            with open(self.impl_path, 'r') as f:
                return parse(f.read())
        else:
            svgen_log().warning(
                f'SystemVerilog file not found for {self.node.name}')

    def get_synth_wrap(self, template_env):
        context = {
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


# class SVGenSVModPlugin(SVGenPlugin):
#     @classmethod
#     def bind(cls):
#         safe_bind('svgen/module_namespace/Gear', SVModuleGen)
#         safe_bind('svgen/module_namespace/GearHierRoot', SVModuleGen)
