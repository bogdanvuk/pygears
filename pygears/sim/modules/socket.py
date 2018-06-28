import socket
import asyncio
import array
import os
import jinja2
import math
from math import ceil
import time

import itertools
from importlib import util

from pygears.svgen.util import svgen_typedef
from pygears.svgen import svgen
from pygears.definitions import ROOT_DIR
from pygears import registry, GearDone
from pygears.sim.sim_gear import SimGear
from pygears.util.fileio import save_file
from pygears.typing_common.codec import code, decode

from pygears.sim import delta, clk


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


def sv_cosim_gen(gear):
    pygearslib = util.find_spec("pygearslib")
    if pygearslib is not None:
        from pygearslib import sv_src_path
        registry('SVGenSystemVerilogPaths').append(sv_src_path)

    outdir = registry('SimArtifactDir')

    rtl_node = svgen(gear, outdir=outdir)
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
        'out_path': outdir,
        'activity_timeout': 1000  # in clk cycles
    }
    context['includes'] = []
    context['imports'] = registry('SVGenSystemVerilogImportPaths')

    if pygearslib is not None:
        context['includes'].append(
            os.path.abspath(os.path.join(sv_src_path, '*.sv')))

    context['includes'].append(
        os.path.abspath(os.path.join(ROOT_DIR, '..', 'svlib', '*.sv')))
    context['includes'].append(
        os.path.abspath(os.path.join(ROOT_DIR, 'cookbook', 'svlib', '*.sv')))
    context['includes'].append(os.path.abspath(os.path.join(outdir, '*.sv')))

    for templ, tname in zip(j2_templates, j2_file_names):
        res = env.get_template(templ).render(context)
        fname = save_file(tname, context['out_path'], res)
        if os.path.splitext(fname)[1] == '.sh':
            os.chmod(fname, 0o777)


class SimSocket(SimGear):
    def __init__(self, gear):
        super().__init__(gear)

        sv_cosim_gen(gear)

        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ('localhost', 1234)
        print('starting up on %s port %s' % server_address)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        # self.sock.setblocking(True)

        self.sock.bind(server_address)

        # Listen for incoming connections
        self.sock.listen(len(gear.in_ports) + len(gear.out_ports))
        self.handlers = {}

    async def in_handler(self, conn, pin):
        din = pin.consumer
        try:
            while True:
                async with din as item:
                    pkt = u32_repr(item, din.dtype).tobytes()
                    await self.loop.sock_sendall(conn, pkt)
                    await self.loop.sock_recv(conn, 1024)

        except GearDone as e:
            print(f"SimGear canceling: socket@{pin.basename}")
            del self.handlers[pin]
            conn.send(b'\x00')
            conn.close()

            # If only synchro remains...
            if len(self.handlers) == 1:
                self.finish()
                raise e

        except Exception as e:
            print(f"Exception in socket handler {pin.basename}: {e}")

    async def out_handler(self, conn, pout):
        dout = pout.producer
        try:
            while True:
                # recv buffer size must be a multiple of 4 bytes
                buff_size = math.ceil(int(dout.dtype) / 8)
                if buff_size < 4:
                    buff_size = 4
                if buff_size % 4:
                    buff_size += 4 - (buff_size % 4)
                item = await self.loop.sock_recv(conn, buff_size)

                if not item:
                    raise GearDone

                # print(f"Output data {item}, of len {len(item)}")

                await dout.put(u32_bytes_decode(item, dout.dtype))

        except GearDone as e:
            print(f"SimGear canceling: socket@{pout.basename}")
            del self.handlers[pout]
            dout.finish()
            conn.close()
            # If only synchro remains...
            if len(self.handlers) == 1:
                self.finish()
                raise e

        except Exception as e:
            print(f"Exception in socket handler {pout.basename}: {e}")

    async def synchro_handler(self, conn, pin):
        try:
            conn.setblocking(True)
            # cadence_time = 0
            # python_time = 0
            # start = None
            # end = None
            # cnt = 0

            while True:
                await delta()
                # print("Sending synchro info")
                # start = time.time()
                # if end is not None:
                #     python_time += start - end

                conn.send(b'\x00')
                conn.recv(4)
                # end = time.time()
                # cnt += 1

                # cadence_time += end - start

                # if (cnt % 1000) == 0:
                #     print(f'Cadence time: {cadence_time/1000}')
                #     print(f'Python time: {python_time/999}')
                #     cadence_time = 0
                #     python_time = 0

                # print("Cadence clock done")
                # print(asyncio.get_event_loop()._ready)
                # print(asyncio.get_event_loop()._scheduled)
                await clk()

        except GearDone as e:
            print(f"SimGear canceling: socket@{pin.basename}")
            del self.handlers[pin]
            conn.send(b'\x00')
            conn.close()

            if not self.handlers:
                self.finish()

            # raise e
        except Exception as e:
            print(f"Exception in socket handler {pin.basename}: {e}")

    def make_in_handler(self, name, conn, args):
        try:
            i = self.gear.argnames.index(name)
            return self.gear.in_ports[i], self.in_handler(
                conn, self.gear.in_ports[i])

        except ValueError as e:
            return None, None

    def make_out_handler(self, name, conn, args):
        try:
            i = self.gear.outnames.index(name)
            return self.gear.out_ports[i], self.out_handler(
                conn, self.gear.out_ports[i])

        except ValueError as e:
            return None, None

    def make_synchro_handler(self, name, conn, args):
        try:
            return name, self.synchro_handler(conn, name)

        except ValueError as e:
            return None, None

    def finish(self):
        print("Closing socket server")
        super().finish()
        for h in self.handlers.values():
            h.cancel()

        self.sock.close()

    async def func(self, *args, **kwds):
        await asyncio.gather(*self.handlers.values())
        raise GearDone

    async def setup(self, *args, **kwds):
        self.loop = asyncio.get_event_loop()

        print(self.gear.argnames)

        total_conn_num = len(self.gear.argnames) + len(self.gear.outnames) + 1
        conn_num = 0
        while conn_num != total_conn_num:
            print("Wait for connection")
            conn, addr = await self.loop.sock_accept(self.sock)

            msg = await self.loop.sock_recv(conn, 1024)
            port_name = msg.decode()

            print(f"Connection received for {port_name}")

            if port_name == '_synchro':
                print("Trying synchro port")
                port, handler = self.make_synchro_handler(
                    port_name, conn, args)
            else:
                port, handler = self.make_in_handler(port_name, conn, args)
                if handler is None:
                    print("Trying in port")
                    port, handler = self.make_out_handler(
                        port_name, conn, args)

                if handler is None:
                    print(f"Nonexistant port {port_name}")
                    conn.close()
                    continue

            self.handlers[port] = handler
            conn_num += 1
