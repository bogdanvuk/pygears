from pygears import registry, bind
from pygears.sim import timestep
from pygears.typing_common.codec import code
from pygears.typing import typeof, TLM
from vcd import VCDWriter
import os
import fnmatch


def match(val, include_pattern):
    return any(fnmatch.fnmatch(val, p) for p in include_pattern)


def register_traces_for_intf(dtype, scope, writer):
    if typeof(dtype, TLM):
        vcd_data = writer.register_var(scope, f'{scope}.data', 'string')
    else:
        vcd_data = writer.register_var(
            scope, f'{scope}.data', 'wire', size=int(dtype))

    vcd_valid = writer.register_var(
        scope, f'{scope}.valid', 'wire', size=1, init=0)
    vcd_ready = writer.register_var(
        scope, f'{scope}.ready', 'wire', size=1, init=0)

    return {'data': vcd_data, 'valid': vcd_valid, 'ready': vcd_ready}


class VCD:
    def __init__(self, top, conf):
        vcd_file = open(
            os.path.join(registry('SimArtifactDir'), 'pygears.vcd'), 'w')

        if 'vcd_include' in conf:
            vcd_include = conf['vcd_include']
        else:
            vcd_include = []

        if 'vcd_tlm' in conf:
            vcd_tlm = conf['vcd_tlm']
        else:
            vcd_tlm = False

        self.writer = VCDWriter(vcd_file, timescale='1 ns', date='today')
        bind('VCDWriter', self.writer)

        sim = registry('Simulator')
        sim.events['before_timestep'].append(self.before_timestep)
        sim.events['after_timestep'].append(self.after_timestep)
        sim.events['after_run'].append(self.after_run)
        self.clk_var = self.writer.register_var(
            '', 'clk', 'wire', size=1, init=1)

        self.vcd_vars = {}
        self.handhake = set()

        sim_map = registry('SimMap')
        for module, sim_gear in sim_map.items():
            gear_vcd_scope = module.name[1:].replace('/', '.')

            for p in module.out_ports:
                if not match(f'{module.name}.{p.basename}', vcd_include):
                    continue

                if (p.dtype is None) or (typeof(p.dtype, TLM) and not vcd_tlm):
                    continue

                scope = '.'.join([gear_vcd_scope, p.basename])
                intf = p.producer

                self.vcd_vars[intf] = register_traces_for_intf(
                    p.dtype, scope, self.writer)

                intf.events['put'].append(self.intf_put)
                intf.events['ack'].append(self.intf_ack)

    def intf_put(self, intf, val):
        v = self.vcd_vars[intf]

        if typeof(intf.dtype, TLM):
            self.writer.change(v['data'], timestep() * 10, str(val))
        else:
            self.writer.change(v['data'],
                               timestep() * 10, code(intf.dtype, val))

        self.writer.change(v['valid'], timestep() * 10, 1)
        return True

    def intf_ack(self, intf):
        v = self.vcd_vars[intf]
        self.writer.change(v['ready'], timestep() * 10, 1)
        self.handhake.add(intf)
        return True

    def before_timestep(self, sim, timestep):
        self.writer.change(self.clk_var, timestep * 10 + 5, 0)
        return True

    def after_timestep(self, sim, timestep):
        self.writer.change(self.clk_var, timestep * 10, 1)
        for intf, v in self.vcd_vars.items():
            if intf in self.handhake:
                self.writer.change(v['ready'], timestep * 10, 0)
                self.writer.change(v['valid'], timestep * 10, 0)
                self.handhake.remove(intf)

        return True

    def after_run(self, sim):
        self.writer.close()
        return True


# class SimVCDPlugin(SimPlugin):
#     @classmethod
#     def bind(cls):
#         cls.registry['SimFlow'].append(VCD)
