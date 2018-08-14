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

from pygears import GearDone, registry
from pygears.definitions import ROOT_DIR
from pygears.sim import clk, sim_log
from pygears.sim.modules.cosim_base import CosimBase, CosimNoData
from pygears.svgen import svgen
from pygears.svgen.util import svgen_typedef
from pygears.typing import Uint
from pygears.typing_common.codec import code, decode
from pygears.util.fileio import save_file


class CosimulatorStartError(Exception):
    pass


async def drive_reset(duration):
    simsoc = registry('SimConfig')['SimSocket']
    await clk()
    data = simsoc.send_req(duration | (1 << 31), Uint[4])
    for i in range(duration):
        await clk()

    return data


def u32_repr_gen(data, dtype):
    yield int(dtype)
    for i in range(ceil(int(dtype) / 32)):
        yield data & 0xffffffff
        data >>= 32


def u32_repr(data, dtype):
    return array.array('I', u32_repr_gen(code(dtype, data), dtype))


def u32_bytes_to_int(data):
    arr = array.array('I')
    arr.frombytes(data)
    val = 0
    for val32 in reversed(arr):
        val <<= 32
        val |= val32

    return val


def u32_bytes_decode(data, dtype):
    return decode(dtype, u32_bytes_to_int(data))


j2_templates = ['runsim.j2', 'top.j2']
j2_file_names = ['run_sim.sh', 'top.sv']


def sv_cosim_gen(gear, tcp_port=1234):
    # pygearslib = util.find_spec("pygearslib")
    # if pygearslib is not None:
    #     from pygearslib import sv_src_path
    #     registry('SVGenSystemVerilogPaths').append(sv_src_path)

    outdir = registry('SimArtifactDir')
    if 'SimSocketHooks' in registry('SimConfig'):
        hooks = registry('SimConfig')['SimSocketHooks']
    else:
        hooks = {}

    srcdir = os.path.join(outdir, 'src_gen')
    rtl_node = svgen(gear, outdir=srcdir)
    sv_node = registry('SVGenMap')[rtl_node]

    port_map = {
        port.basename: port.basename
        for port in itertools.chain(rtl_node.in_ports, rtl_node.out_ports)
    }

    structs = [
        svgen_typedef(port.dtype, f"{port.basename}")
        for port in itertools.chain(rtl_node.in_ports, rtl_node.out_ports)
    ]

    base_addr = os.path.dirname(__file__)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(base_addr),
        trim_blocks=True,
        lstrip_blocks=True)
    env.globals.update(zip=zip, int=int, print=print, issubclass=issubclass)

    context = {
        'intfs': list(sv_node.sv_port_configs()),
        'module_name': sv_node.sv_module_name,
        'dut_name': sv_node.sv_module_name,
        'dti_verif_path': os.path.abspath(
            os.path.join(ROOT_DIR, 'sim', 'dpi')),
        'param_map': sv_node.params,
        'structs': structs,
        'port_map': port_map,
        'out_path': os.path.abspath(outdir),
        'hooks': hooks,
        'rst_mask': "32'h8000_0000",
        'port': tcp_port,
        'activity_timeout': 1000  # in clk cycles
    }

    inc_paths = []
    context['includes'] = []
    for path in registry('SVGenSystemVerilogPaths'):
        inc_paths.append(path)
    inc_paths.append(srcdir)
    inc_paths.append(outdir)

    context['includes'] = [
        os.path.abspath(os.path.join(p, '*.sv')) for p in inc_paths
        if os.path.exists(p)
    ]

    # remove empty wildcard imports
    context['includes'] = [p for p in context['includes'] if glob.glob(p)]

    for templ, tname in zip(j2_templates, j2_file_names):
        res = env.get_template(templ).render(context)
        fname = save_file(tname, context['out_path'], res)
        if os.path.splitext(fname)[1] == '.sh':
            os.chmod(fname, 0o777)


class SimSocketDrv:
    def __init__(self, handler, port):
        self.handler = handler
        self.port = port

    def reset(self):
        pass


class SimSocketInputDrv(SimSocketDrv):
    def close(self):
        self.handler.sendall(b'\x00\x00\x00\x00')
        self.handler.close()
        # del self.handler

    def send(self, data):
        # print(f'Sending {repr(data)} for {self.port.basename} of type {self.port.dtype}')
        pkt = u32_repr(data, self.port.dtype).tobytes()
        self.handler.sendall(pkt)

    def ready(self):
        try:
            self.handler.recv(4)
            return True
        except socket.error:
            return False


class SimSocketOutputDrv(SimSocketDrv):
    def read(self):
        buff_size = math.ceil(int(self.port.dtype) / 8)
        if buff_size < 4:
            buff_size = 4
        if buff_size % 4:
            buff_size += 4 - (buff_size % 4)
        try:
            data = self.handler.recv(buff_size)
            return u32_bytes_decode(data, self.port.dtype)
        except socket.error:
            raise CosimNoData

    def ack(self):
        try:
            self.handler.sendall(b'\x01\x00\x00\x00')
        except socket.error:
            raise GearDone


class SimSocketSynchro:
    def __init__(self, handler):
        self.handler = handler
        self.handler.settimeout(5.0)

    def cycle(self):
        pass

    def forward(self):
        data = None
        while not data:
            try:
                self.handler.sendall(b'\x00\x00\x00\x00')
                data = self.handler.recv(4)
            except socket.timeout:
                import pdb
                pdb.set_trace()
            except socket.error:
                raise GearDone

    back = forward

    def sendall(self, pkt):
        self.handler.sendall(pkt)

    def recv(self, buff_size):
        return self.handler.recv(buff_size)


class SimSocket(CosimBase):
    def __init__(self,
                 gear,
                 rebuild=True,
                 run=False,
                 batch=True,
                 tcp_port=1234,
                 **kwds):
        super().__init__(gear)

        self.rebuild = rebuild

        # Create a TCP/IP socket
        self.run_cosim = run
        kwds['batch'] = batch
        self.kwds = kwds
        self.sock = None

        self.server_address = ('localhost', tcp_port)
        self.handlers = {}

        registry('SimConfig')['SimSocket'] = self

    def finish(self):
        sim_log().debug(f'Closing socket server')
        super().finish()

    def cleanup(self):
        if self.sock:
            sim_log().info(f'Done. Closing the socket...')
            time.sleep(3)
            self.sock.close()
            time.sleep(1)

            if self.cosim_pid is not None:
                self.cosim_pid.terminate()

        super().cleanup()

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

    def setup(self):
        super().setup()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the port
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind(self.server_address)

        # Listen for incoming connections
        self.sock.listen(len(self.gear.in_ports) + len(self.gear.out_ports))

        if self.rebuild:
            sv_cosim_gen(self.gear, self.server_address[1])

        self.cosim_pid = None
        if self.run_cosim:

            self.sock.settimeout(1)

            outdir = registry('SimArtifactDir')
            args = ' '.join(f'-{k} {v if not isinstance(v, bool) else ""}'
                            for k, v in self.kwds.items()
                            if not isinstance(v, bool) or v)
            if 'seed' in self.kwds:
                sim_log().warning(
                    'Separately set seed for cosimulator. Ignoring SimRandSeed.'
                )
            else:
                args += f' -seed {registry("SimRandSeed")}'
            if sim_log().isEnabledFor(logging.DEBUG):
                stdout = None
            else:
                stdout = DEVNULL

            sim_log().info(f'Running cosimulator with: {args}')
            self.cosim_pid = Popen(
                [f'./run_sim.sh'] + args.split(' '),
                stdout=stdout,
                stderr=stdout,
                cwd=outdir)
            time.sleep(0.1)
            ret = self.cosim_pid.poll()
            if ret is not None:
                sim_log().error(f"Cosimulator error: {ret}")
                raise CosimulatorStartError
            else:
                sim_log().info(f"Cosimulator started")

        self.loop = asyncio.get_event_loop()

        total_conn_num = len(self.gear.argnames) + len(self.gear.outnames) + 1

        sim_log().info(f'Waiting on {self.sock.getsockname()}')
        while len(self.handlers) != total_conn_num:
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
                self.sock.listen(1)
                conn, addr = self.sock.accept()

            msg = conn.recv(1024)
            port_name = msg.decode()

            if port_name == self.SYNCHRO_HANDLE_NAME:
                self.handlers[self.SYNCHRO_HANDLE_NAME] = SimSocketSynchro(
                    conn)
                # conn.setblocking(True)
            else:
                for p in self.gear.in_ports:
                    if p.basename == port_name:
                        self.handlers[port_name] = SimSocketInputDrv(conn, p)
                        break
                for p in self.gear.out_ports:
                    if p.basename == port_name:
                        self.handlers[port_name] = SimSocketOutputDrv(conn, p)
                        break
                conn.setblocking(False)

            sim_log().debug(f"Connection received for {port_name}")
