import fnmatch
import functools
from collections import OrderedDict

from pygears import reg
from pygears.core.gear import OutSig
# from .inst import SVGenInstPlugin
# from pygears.hdl.sv.svparse import parse
from pygears.hdl.modinst import HDLModuleInst
from pygears.hdl import hdl_log

from .vcompile import compile_gear
from ..sv.svparse import parse
from ..sv.sv_keywords import sv_keywords as keywords


class VModuleInst(HDLModuleInst):
    def __init__(self, node):
        super().__init__(node, 'v')
        self.vgen_map = reg['vgen/map']

    @property
    def inst_name(self):
        inst_name = super().inst_name

        if inst_name in keywords:
            return f'{inst_name}_i'
        else:
            return inst_name

    @property
    @functools.lru_cache()
    def traced(self):
        self_traced = any(
            fnmatch.fnmatch(self.node.name, p)
            for p in reg['debug/trace'])

        if self.is_hierarchical:
            children_traced = any(self.vgen_map[child].traced
                                  for child in self.node.child)
        else:
            children_traced = False

        return self_traced or children_traced

    @functools.lru_cache()
    def impl_parse(self):
        if self.impl_path:
            # raise Exception('parse not implemented')
            with open(self.impl_path, 'r') as f:
                return parse(f.read())
        else:
            hdl_log().warning(f'Verilog file not found for {self.node.name}')

    def get_synth_wrap(self, template_env):
        context = {
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'intfs': list(self.port_configs),
            'sigs': self.node.meta_kwds['signals'],
            'param_map': self.params
        }
        return template_env.render_local(__file__, "module_synth_wrap.j2",
                                         context)

    def get_out_port_map_intf_name(self, port):
        return self.vgen_map[port.consumer].basename, None, None

    def get_in_port_map_intf_name(self, port):
        intf = port.producer
        vgen_intf = self.vgen_map[intf]

        if len(intf.consumers) == 1:
            return vgen_intf.outname, None, None
        else:
            return (vgen_intf.outname, intf.consumers.index(port),
                    intf.dtype.width)

    def get_compiled_module(self, template_env):
        return compile_gear(self.node.gear, template_env, self.module_context)

    def get_hier_module(self, template_env):
        context = self.module_context

        self.vgen_map = reg['vgen/map']

        for child in self.node.local_interfaces():
            vgen = self.vgen_map[child]
            contents = vgen.get_inst(template_env)
            if contents:
                context['inst'].append(contents)

        for child in self.node.local_modules():
            for s in child.meta_kwds['signals']:
                if isinstance(s, OutSig):
                    name = child.params['sigmap'][s.name]
                    context['inst'].append(f'logic [{s.width-1}:0] {name};')

            vgen = self.vgen_map[child]
            if hasattr(vgen, 'get_inst'):
                contents = vgen.get_inst(template_env)
                if contents:
                    if vgen.traced:
                        context['inst'].append('/*verilator tracing_on*/')
                    context['inst'].append(contents)
                    if vgen.traced:
                        context['inst'].append('/*verilator tracing_off*/')

        return template_env.render_local(__file__, "hier_module.j2", context)

    def get_inst(self, template_env):
        param_map = self.params

        port_map = {
            port.basename: self.get_in_port_map_intf_name(port)
            for port in self.node.in_ports
        }

        port_map.update({
            port.basename: self.get_out_port_map_intf_name(port)
            for port in self.node.out_ports
        })

        context = {
            'rst_name': 'rst',
            'module_name': self.module_name,
            'inst_name': self.inst_name,
            'param_map': param_map,
            'port_map': port_map,
            'sig_map': self.node.params['sigmap']
        }

        return template_env.snippets.module_inst(**context)

