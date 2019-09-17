import fnmatch
import functools
from string import Template

from pygears import PluginBase, registry, safe_bind
from pygears.conf import Inject, inject, config
from pygears.rtl.port import OutPort, InPort
from .util import svgen_typedef

dti_spy_connect_t = Template("""
dti_spy #(${intf_name}_t) _${intf_name}(clk, rst);
assign _${intf_name}.data = ${conn_name}.data;
assign _${intf_name}.valid = ${conn_name}.valid;
assign _${intf_name}.ready = ${conn_name}.ready;""")


class SVIntfGen:
    def __init__(self, intf):
        self.intf = intf

    @property
    def basename(self):
        return self.intf.basename

    @property
    def outname(self):
        return self.intf.outname

    @property
    @functools.lru_cache()
    def traced(self):
        return any(
            fnmatch.fnmatch(self.intf.name, p)
            for p in registry('hdl/debug_intfs'))

    @inject
    def get_inst(self,
                 template_env,
                 spy_connect_t=Inject('svgen/spy_connection_template')):

        if self.intf.producer is None:
            return

        inst = []
        if not self.intf.is_port_intf:
            inst.append(self.get_intf_def(self.basename, 1, template_env))

        if self.intf.is_broadcast:
            inst.extend([
                self.get_intf_def(self.outname, len(self.intf.consumers),
                                  template_env),
                self.get_bc_module(template_env)
            ])

            if self.traced:
                for i in range(len(self.intf.consumers)):
                    intf_name = f'{self.outname}_{i}'
                    conn_name = f'{self.outname}[{i}]'
                    inst.extend(
                        svgen_typedef(self.intf.dtype, intf_name).split('\n'))

                    inst.extend(
                        spy_connect_t.substitute(
                            intf_name=intf_name,
                            conn_name=conn_name).split('\n'))

        for i, cons_port in enumerate(self.intf.consumers):
            if isinstance(cons_port, OutPort):
                if self.intf.is_broadcast or isinstance(
                        self.intf.producer, InPort):
                    din_name = self.outname
                    if self.intf.is_broadcast:
                        din_name += f'[{i}]'

                    inst.append(
                        template_env.snippets.intf_intf_connect(
                            self.intf.consumers[i].basename, din_name))

        if self.traced:
            inst.extend(
                svgen_typedef(self.intf.dtype, self.basename).split('\n'))

            inst.extend(
                spy_connect_t.substitute(intf_name=self.basename,
                                         conn_name=self.basename).split('\n'))

        return '\n'.join(inst)

    def get_intf_def(self, name, size, template_env):
        ctx = {
            'name': name,
            'width': int(self.intf.dtype),
            'size': size,
            'type': str(self.intf.dtype)
        }

        return template_env.snippets.intf_inst(**ctx)

    def get_bc_module(self, template_env):
        inst_name = f'bc_{self.basename}'
        if inst_name.endswith('_if_s'):
            inst_name = inst_name[:-len('_if_s')]

        rst_name = 'local_rst' if registry("svgen/map")[
            self.intf.parent].has_local_rst else 'rst'

        bc_context = {
            'rst_name': rst_name,
            'module_name': 'bc',
            'inst_name': inst_name,
            'param_map': {
                'SIZE': len(self.intf.consumers)
            },
            'port_map': {
                'din': self.basename,
                'dout': self.outname
            }
        }

        return template_env.snippets.module_inst(**bc_context)


class SVGenIntfPlugin(PluginBase):
    @classmethod
    def bind(cls):
        config.define('hdl/debug_intfs', default=[])

        safe_bind('svgen/spy_connection_template', dti_spy_connect_t)
