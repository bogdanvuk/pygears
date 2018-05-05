from collections import OrderedDict

from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svparse import parse
from pygears.definitions import ROOT_DIR
from pygears import registry
from pygears.svgen.svstruct import SVStruct

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

        try:
            self.sv_module_path, self._sv_module_name, self.sv_params = self.get_sv_module_info()
        except FileNotFoundError:
            pass

    @property
    def sv_module_name(self):
        return self._sv_module_name or self.node.basename

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

        raise FileNotFoundError

    def get_params(self):
        return {
            k.upper(): int(v)
            for k, v in self.node.params.items()
            if (k.upper() in self.sv_params) and (
                int(v) != int(self.sv_params[k.upper()]['val']))
        }

    def sv_port_configs(self):
        for p in self.node.in_ports:
            yield self.get_sv_port_config(
                'consumer', type_=p.producer.dtype, name=p.basename)

        for p in self.node.out_ports:
            yield self.get_sv_port_config(
                'producer', type_=p.consumer.dtype, name=p.basename)

    def get_sv_port_config(self, modport, type_, name):
        return {
            'modport': modport,
            'name': name,
            'type': str(type_),
            'width': int(type_),
            'struct': SVStruct(name, type_)
        }

    def get_synth_wrap(self):

        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'param_map': self.get_params()
        }
        return self.context.jenv.get_template("module_synth_wrap.j2").render(
            **context)

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

    def get_module(self, template_env):
        pass

    def update_port_name(self, port, name):
        port['name'] = name

    def get_inst(self, template_env):
        param_map = self.get_params()

        in_port_map = [(port.basename, self.get_in_port_map_intf_name(port))
                       for port in self.node.in_ports]

        out_port_map = [(port.basename, self.get_out_port_map_intf_name(port))
                        for port in self.node.out_ports]

        context = {
            'module_name': self.sv_module_name,
            'inst_name': self.sv_inst_name,
            'param_map': param_map,
            'port_map': OrderedDict(in_port_map + out_port_map)
        }

        return template_env.snippets.module_inst(**context)


class SVGenSVModPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Gear'] = SVModuleGen

        cls.registry['SVGenSystemVerilogPaths'].append(
            os.path.join(ROOT_DIR, '..', 'svlib'))
        cls.registry['SVGenSystemVerilogPaths'].append(
            os.path.join(ROOT_DIR, 'cookbook', 'svlib'))
