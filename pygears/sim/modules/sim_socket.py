import itertools
import os
import socket

from pygears import GearDone, reg
from pygears.conf import Inject, inject
from pygears.sim import clk
from pygears.sim.modules.cosim_base import CosimBase, CosimNoData
from pygears.sim.extens.svsock import register_intf
from pygears.hdl import hdlgen, list_hdl_files
from pygears.hdl.sv.util import svgen_typedef
from pygears.hdl.templenv import TemplateEnv

CMD_SYS_RESET = 0x80000000
CMD_SET_DATA = 0x40000000
CMD_RESET = 0x20000000
CMD_FORWARD = 0x10000000
CMD_CYCLE = 0x08000000
CMD_READ = 0x04000000
CMD_ACK = 0x02000000


class CosimulatorStartError(Exception):
    pass


def format_list(list_, pattern):
    return [pattern.format(s) for s in list_]


async def drive_reset(duration):
    simsoc = reg['sim/config/socket']
    await clk()
    simsoc.send_cmd(duration | CMD_SYS_RESET)
    for i in range(duration):
        await clk()

    # return data


class SimSocketDrv:
    @inject
    def __init__(self, port, index, main=Inject('sim/svsock/server')):
        self.main = main
        self.index = index
        self.port = port

    def reset(self):
        pass


class SimSocketInputDrv(SimSocketDrv):
    def send(self, data):
        # print(
        #     f'{timestep()} [{self.port.name}] Sending {hex(data.code())}, {repr(data)}'
        # )
        self.main.send_cmd(CMD_SET_DATA | self.index)
        self.main.dtype_send(data, self.port.dtype)

    def reset(self):
        # print(f'{timestep()} [{self.port.name}] Reset valid')
        self.main.send_cmd(CMD_RESET | self.index)

    def ready(self):
        self.main.send_cmd(CMD_READ | self.index)

        data = self.main.recv(4)
        res = bool(int.from_bytes(data, byteorder='little'))

        # print(f'{timestep()} [{self.port.name}] Ready={res}')
        return res


class SimSocketOutputDrv(SimSocketDrv):
    def read(self):
        # print(
        #     f'{timestep()} [{self.port.name}] Send read command for {self.index}'
        # )
        self.main.send_cmd(CMD_READ | self.index)
        data = self.main.recv(4)
        # print(
        #     f'{timestep()} [{self.port.name}] Received valid status for {self.index}: {data}'
        # )

        if int.from_bytes(data, byteorder='little'):
            return self.main.dtype_recv(self.port.dtype)
        else:
            raise CosimNoData

    def reset(self):
        self.main.send_cmd(CMD_RESET | self.index)

    def ack(self):
        try:
            self.main.send_cmd(CMD_ACK | self.index)
        except socket.error:
            raise GearDone


class SVServerModule:
    def __init__(self, module, tenv, srcdir, rst):
        self.srcdir = srcdir
        self.module = module
        self.tenv = tenv
        self.rst = rst
        from pygears import reg
        self.svmod = reg['hdlgen/map'][self.module]

    def files(self):
        return list_hdl_files(self.module, self.srcdir)

    def includes(self):
        return reg[f'svgen/include'] + [self.srcdir]

    def declaration(self):
        port_map = {
            port.basename: port.basename
            for port in itertools.chain(self.module.in_ports, self.module.out_ports)
        }
        return self.tenv.snippets.module_inst(
            self.svmod.wrap_module_name, self.svmod.params, "dut", port_map, self.rst)


class SVServerIntf:
    def __init__(self, port, tenv):
        self.port = port
        self.name = port.basename
        self.dtype = port.dtype
        self.tenv = tenv

    def declaration(self):
        return '\n'.join(
            [
                svgen_typedef(self.dtype, f"{self.name}"),
                f"dti_verif_if#({self.name}_t) {self.name}_vif (clk, rst);",
                f"dti#({self.dtype.width}) {self.name} ();",
                f"bit[{self.dtype.width-1}:0] {self.name}_data;",
                self.tenv.snippets.connect_vif(self.name, self.port.direction),
            ])

    def init(self):
        if self.port.direction == "in":
            return '\n'.join(
                [
                    f'{self.name}_vif.name = "{self.name}";',
                    f"{self.name}_vif.valid <= 1'b0;",
                ])
        else:
            return '\n'.join(
                [
                    f'{self.name}_vif.name = "{self.name}";',
                    f"{self.name}_vif.ready <= 1'b0;",
                ])

    def set_data(self):
        if self.port.direction == 'in':
            return self.tenv.snippets.set_data(self.name, self.dtype.width)

    def read(self):
        return self.tenv.snippets.read(self.name, self.port.direction)

    def ack(self):
        if self.port.direction == 'out':
            return self.tenv.snippets.ack(self.name)

    def reset(self):
        return self.tenv.snippets.reset(self.name, self.port.direction)

    def sys_reset(self):
        return self.tenv.snippets.sys_reset(self.name, self.port.direction)


class SimSocket(CosimBase):
    def __init__(self, gear, timeout=100, rebuild=True, run=True, batch=True, rst=True, **kwds):
        super().__init__(gear, timeout)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.abspath(os.path.join(reg['results-dir'], self.name))

        self.rebuild = rebuild

        reg['sim/svsock/run'] = run

        if not kwds.get('gui', False):
            kwds['batch'] = batch

        self.rst = rst
        self.kwds = kwds
        self.sock = None
        self.cosim_pid = None

        self.handlers = {}

        reg['sim/config/socket'] = self

        self.srcdir = os.path.join(self.outdir, 'src_gen')
        self.rtl_node = hdlgen(gear, outdir=self.srcdir, lang='sv')
        self.svmod = reg['hdlgen/map'][self.rtl_node]

    def cycle(self):
        self.send_cmd(CMD_CYCLE)

    def forward(self):
        self.send_cmd(CMD_FORWARD)

    back = forward

    def setup(self):
        basedir = os.path.dirname(__file__)
        tenv = TemplateEnv(basedir)
        tenv.snippets = tenv.load(basedir, 'svsock_intf.j2').module

        for cp in self.in_cosim_ports:
            sock_id = register_intf(SVServerIntf(cp.port, tenv))
            self.handlers[cp.port.basename] = SimSocketInputDrv(cp.port, sock_id)

        for p in self.gear.out_ports:
            sock_id = register_intf(SVServerIntf(p, tenv))
            self.handlers[p.basename] = SimSocketOutputDrv(p, sock_id)

        register_intf(SVServerModule(self.rtl_node, tenv, self.srcdir, rst=self.rst))

        self.conn = reg['sim/svsock/server']
        self.send_cmd = self.conn.send_cmd

        super().setup()
