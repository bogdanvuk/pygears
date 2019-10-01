import array
import asyncio
import glob
import itertools
import logging
import math
import os
import socket
import time
from math import ceil
from subprocess import DEVNULL, Popen

import jinja2

from pygears import GearDone, bind, registry
from pygears.definitions import ROOT_DIR
from pygears.sim import clk, sim_log, timestep
from pygears.sim.modules.cosim_base import CosimBase, CosimNoData
from .cosim_port import InCosimPort
from pygears.core.port import InPort
from pygears.core.graph import closest_gear_port_from_rtl
from pygears.hdl import hdlgen
from pygears.hdl.sv.util import svgen_typedef
from pygears.util.fileio import save_file
from pygears.hdl.templenv import isinput, isoutput, keymap
from pygears.synth.common import list_hdl_files

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
    simsoc = registry('sim/config/socket')
    await clk()
    simsoc.send_cmd(duration | CMD_SYS_RESET)
    for i in range(duration):
        await clk()

    # return data


def u32_repr_gen(data, dtype):
    for i in range(ceil(int(dtype) / 32)):
        yield data & 0xffffffff
        data >>= 32


def u32_repr(data, dtype):
    return array.array('I', u32_repr_gen(dtype(data).code(), dtype))


def u32_bytes_to_int(data):
    arr = array.array('I')
    arr.frombytes(data)
    val = 0
    for val32 in reversed(arr):
        val <<= 32
        val |= val32

    return val


def u32_bytes_decode(data, dtype):
    return dtype.decode(u32_bytes_to_int(data) & ((1 << int(dtype)) - 1))


j2_templates = ['runsim.j2', 'top.j2']
j2_file_names = ['run_sim.sh', 'top.sv']


class SimSocketDrv:
    def __init__(self, main, port):
        self.main = main
        self.port = port

    def reset(self):
        pass


class SimSocketInputDrv(SimSocketDrv):
    def close(self):
        self.main.sendall(b'\x00\x00\x00\x00')
        self.main.close()
        # del self.main

    def send(self, data):
        # print(
        #     f'{timestep()} [{self.port.name}] Sending {hex(data.code())}, {repr(data)}'
        # )
        self.main.send_cmd(CMD_SET_DATA | self.port.index)
        pkt = u32_repr(data, self.port.dtype).tobytes()
        self.main.sendall(pkt)

    def reset(self):
        # print(f'{timestep()} [{self.port.name}] Reset valid')
        self.main.send_cmd(CMD_RESET | self.port.index)

    def ready(self):
        self.main.send_cmd(CMD_READ | self.port.index)

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
            buff_size = math.ceil(int(self.port.dtype) / 8)
            if buff_size < 4:
                buff_size = 4
            if buff_size % 4:
                buff_size += 4 - (buff_size % 4)

            data = self.main.recv(buff_size)
            return u32_bytes_decode(data, self.port.dtype)
        else:
            raise CosimNoData

    def reset(self):
        self.main.send_cmd(CMD_RESET | self.index)

    @property
    def index(self):
        return len(self.main.in_cosim_ports) + self.port.index

    def ack(self):
        try:
            self.main.send_cmd(CMD_ACK | self.index)
        except socket.error:
            raise GearDone


class SimSocketSynchro:
    def __init__(self, main, handler):
        self.main = main
        self.handler = handler
        # self.handler.settimeout(5.0)

    def cycle(self):
        # print(f'{timestep()} Cycle')
        self.main.send_cmd(CMD_CYCLE)

    def forward(self):
        # print(f'{timestep()} Forward')
        self.main.send_cmd(CMD_FORWARD)

    back = forward

    def sendall(self, pkt):
        # print(f'Sending: {pkt}')
        self.handler.sendall(pkt)

    def recv(self, buff_size):
        return self.handler.recv(buff_size)


class SimSocket(CosimBase):
    def __init__(self,
                 gear,
                 timeout=100,
                 rebuild=True,
                 run=False,
                 batch=True,
                 tcp_port=1234,
                 **kwds):
        super().__init__(gear, timeout)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.abspath(
            os.path.join(registry('results-dir'), self.name))

        self.rebuild = rebuild

        # Create a TCP/IP socket
        self.run_cosim = run

        if not kwds.get('gui', False):
            kwds['batch'] = batch

        self.kwds = kwds
        self.sock = None
        self.cosim_pid = None

        self.server_address = ('localhost', tcp_port)
        self.handlers = {}

        bind('sim/config/socket', self)

        self.srcdir = os.path.join(self.outdir, 'src_gen')
        self.rtl_node = hdlgen(gear, outdir=self.srcdir, language='sv')
        self.svmod = registry('svgen/map')[self.rtl_node]

        for p in self.rtl_node.in_ports:
            if p.index >= len(gear.in_ports):
                driver = closest_gear_port_from_rtl(p, 'in')
                consumer = closest_gear_port_from_rtl(p, 'out')

                in_port = InPort(gear,
                                 p.index,
                                 p.basename,
                                 producer=driver.producer,
                                 consumer=consumer.consumer)

                self.in_cosim_ports.append(InCosimPort(self, in_port))
                registry('sim/map')[in_port] = self.in_cosim_ports[-1]

    def _cleanup(self):
        if self.sock:
            # sim_log().info(f'Done. Closing the socket...')
            # time.sleep(3)
            self.sock.close()
            time.sleep(1)

            if self.cosim_pid is not None:
                self.cosim_pid.terminate()

        super()._cleanup()

    def sendall(self, pkt):
        self.handlers[self.SYNCHRO_HANDLE_NAME].sendall(pkt)

    def send_cmd(self, req):
        # cmd_name = [k for k, v in globals().items() if v == (req & 0xffff0000)][0]
        # print(f'SimSocket: sending command {cmd_name}')
        pkt = req.to_bytes(4, byteorder='little')
        self.handlers[self.SYNCHRO_HANDLE_NAME].sendall(pkt)

    def recv(self, size):
        return self.handlers[self.SYNCHRO_HANDLE_NAME].recv(size)

    def send_req(self, req, dtype):
        # print('SimSocket sending request...')
        data = None

        # Send request
        pkt = req.to_bytes(4, byteorder='little')
        self.handlers[self.SYNCHRO_HANDLE_NAME].sendall(b'\x01\x00\x00\x00' +
                                                        pkt)

        # Get random data
        while data is None:
            try:
                buff_size = math.ceil(int(dtype) / 8)
                if buff_size < 4:
                    buff_size = 4
                if buff_size % 4:
                    buff_size += 4 - (buff_size % 4)
                data = self.handlers[self.SYNCHRO_HANDLE_NAME].recv(buff_size)
            except socket.error:
                sim_log().error(f'socket error on {self.SYNCHRO_HANDLE_NAME}')
                raise socket.error

        data = u32_bytes_decode(data, dtype)
        return data

    def build(self):
        if 'socket_hooks' in registry('sim/config'):
            hooks = registry('sim/config/socket_hooks')
        else:
            hooks = {}

        port_map = {
            port.basename: port.basename
            for port in itertools.chain(self.rtl_node.in_ports,
                                        self.rtl_node.out_ports)
        }

        structs = [
            svgen_typedef(port.dtype,
                          f"{port.basename}") for port in itertools.chain(
                              self.rtl_node.in_ports, self.rtl_node.out_ports)
        ]

        base_addr = os.path.dirname(__file__)
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(base_addr),
                                 trim_blocks=True,
                                 lstrip_blocks=True)
        env.globals.update(zip=zip,
                           int=int,
                           print=print,
                           issubclass=issubclass)

        env.filters['format_list'] = format_list
        env.filters['isinput'] = isinput
        env.filters['isoutput'] = isoutput
        env.filters['keymap'] = keymap

        sv_files = list_hdl_files(self.rtl_node,
                                  self.srcdir,
                                  language='sv',
                                  wrapper=False)

        context = {
            'intfs': list(self.svmod.port_configs),
            'files': sv_files,
            'module_name': self.svmod.module_name,
            'dut_name': self.svmod.module_name,
            'dti_verif_path':
            os.path.abspath(os.path.join(ROOT_DIR, 'sim', 'dpi')),
            'param_map': self.svmod.params,
            'structs': structs,
            'port_map': port_map,
            'out_path': os.path.abspath(self.outdir),
            'hooks': hooks,
            'port': self.server_address[1],
            'top_name': 'top',
            'activity_timeout': 1000  # in clk cycles
        }

        context['includes'] = []
        context['includes'].extend(self.svmod.include)
        context['includes'].extend(registry('hdl/include'))
        context['includes'].append(self.srcdir)
        context['includes'].append(self.outdir)

        for templ, tname in zip(j2_templates, j2_file_names):
            res = env.get_template(templ).render(context)
            fname = save_file(tname, context['out_path'], res)
            if os.path.splitext(fname)[1] == '.sh':
                os.chmod(fname, 0o777)

    def setup(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        if os.path.exists("/tmp/socket_test.s"):
            os.remove("/tmp/socket_test.s")
        self.sock.bind("/tmp/socket_test.s")

        # Listen for incoming connections
        # self.sock.listen(len(self.gear.in_ports) + len(self.gear.out_ports))
        self.sock.listen(1)

        if self.rebuild:
            self.build()
        else:
            self.kwds['nobuild'] = True

        if self.run_cosim:

            self.sock.settimeout(5)

            args = ' '.join(f'-{k} {v if not isinstance(v, bool) else ""}'
                            for k, v in self.kwds.items()
                            if not isinstance(v, bool) or v)
            if 'seed' in self.kwds:
                sim_log().warning(
                    'Separately set seed for cosimulator. Ignoring sim/rand_seed.'
                )
            else:
                args += f' -seed {registry("sim/rand_seed")}'
            if sim_log().isEnabledFor(logging.DEBUG):
                stdout = None
            else:
                stdout = DEVNULL

            sim_log().info(f'Running cosimulator with: {args}')

            self.cosim_pid = Popen([f'./run_sim.sh'] + args.split(' '),
                                   stdout=stdout,
                                   stderr=stdout,
                                   cwd=self.outdir)
            time.sleep(0.1)
            ret = self.cosim_pid.poll()
            if ret is not None:
                breakpoint()
                sim_log().error(
                    f"Cosimulator error: {ret}. Check log file {self.outdir}/log.log"
                )
                raise CosimulatorStartError
            else:
                sim_log().info(f"Cosimulator started")

        self.loop = asyncio.get_event_loop()

        sim_log().info(f'Waiting on {self.sock.getsockname()}')

        if self.cosim_pid:
            ret = None
            while ret is None:
                try:
                    conn, addr = self.sock.accept()
                    break
                except socket.timeout:
                    ret = self.cosim_pid.poll()
                    if ret is not None:
                        sim_log().error(f"Cosimulator error: {ret}")
                        raise Exception
        else:
            sim_log().debug("Wait for connection")
            conn, addr = self.sock.accept()

        msg = conn.recv(1024)
        port_name = msg.decode()

        self.handlers[self.SYNCHRO_HANDLE_NAME] = SimSocketSynchro(self, conn)

        for cp in self.in_cosim_ports:
            self.handlers[cp.port.basename] = SimSocketInputDrv(self, cp.port)

        for p in self.gear.out_ports:
            self.handlers[p.basename] = SimSocketOutputDrv(self, p)

        sim_log().debug(f"Connection received for {port_name}")
        super().setup()
