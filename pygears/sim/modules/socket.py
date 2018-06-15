import socket
import asyncio
import array
import os
import jinja2
from math import ceil

import itertools
from importlib import util

from pygears.svgen.generate import TemplateEnv
from pygears.svgen.util import svgen_typedef
from pygears.svgen import svgen
from pygears.definitions import ROOT_DIR
from pygears import registry
from pygears.sim.sim_gear import SimGear
from pygears.util.fileio import save_file


def u32_repr_gen(data, dtype):
    yield int(dtype)
    for i in range(ceil(int(dtype) / 32)):
        yield data & 0xffffffff
        data >>= 32


def u32_repr(data, dtype):
    return array.array('I', u32_repr_gen(data, dtype))


def u32_bytes_to_int(data):
    arr = array.array('I')
    arr.frombytes(data)
    val = 0
    for val32 in reversed(arr):
        val <<= 32
        val |= val32

    return val


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
        'out_path': outdir
    }
    context['includes'] = [
        os.path.abspath(os.path.join(ROOT_DIR, '..', 'svlib', '*.sv'))
    ]

    if pygearslib is not None:
        context['includes'].append(
            os.path.abspath(os.path.join(sv_src_path, '*.sv')))

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

        self.sock.bind(server_address)

        # Listen for incoming connections
        self.sock.listen(5)
        self.handlers = []

    async def out_handler(self, conn, din, dtype):
        while True:
            try:
                item = await din.get()
            except asyncio.CancelledError as e:
                await self.loop.sock_sendall(conn, b'\x00')
                conn.close()
                raise e

            pkt = u32_repr(item, dtype).tobytes()
            await self.loop.sock_sendall(conn, pkt)

            try:
                await self.loop.sock_recv(conn, 1024)
            except asyncio.CancelledError as e:
                conn.close()
                raise e

            din.task_done()

    async def in_handler(self, conn, dout_id, dtype):
        try:
            while True:
                print("Wait for input data")
                item = await self.loop.sock_recv(conn, 1024)

                if not item:
                    break

                print(f"Output data {item}, of len {len(item)}")

                await self.output(u32_bytes_to_int(item), dout_id)

        except asyncio.CancelledError as e:
            conn.close()
            raise e
        except Exception as e:
            print(f"Exception in socket handler: {e}")

    def make_out_handler(self, name, conn, args):
        try:
            i = self.gear.argnames.index(name)
            return self.loop.create_task(
                self.out_handler(conn, args[i], self.gear.in_ports[i].dtype))

        except ValueError:
            pass

    def make_in_handler(self, name, conn, args):
        try:
            print(self.gear.outnames)
            print(name)
            i = self.gear.outnames.index(name)
            print(i)
            return self.loop.create_task(
                self.in_handler(conn, i, self.gear.out_ports[i].dtype))

        except ValueError:
            pass

    async def func(self, *args, **kwds):
        self.loop = asyncio.get_event_loop()

        print(self.gear.argnames)

        try:
            while True:
                print("Wait for connection")
                conn, addr = await self.loop.sock_accept(self.sock)

                msg = await self.loop.sock_recv(conn, 1024)
                port_name = msg.decode()

                print(f"Connection received for {port_name}")

                handler = self.make_out_handler(port_name, conn, args)
                if handler is None:
                    print("Trying in port")
                    handler = self.make_in_handler(port_name, conn, args)

                if handler is None:
                    print(f"Nonexistant port {port_name}")
                    conn.close()
                else:
                    self.handlers.append(handler)

        except asyncio.CancelledError as e:
            for h in self.handlers:
                h.cancel()

            raise e
