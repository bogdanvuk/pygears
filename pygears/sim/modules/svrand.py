import math
import os
import socket

import jinja2

from pygears.definitions import ROOT_DIR
from pygears.svgen.util import svgen_typedef
from pygears.util.fileio import save_file
from pygears.sim.modules.socket import u32_bytes_decode, u32_repr


class SVRandCompileError(Exception):
    pass


class SVRandConstraints:
    def __init__(self, name='dflt', cons=[], dtype=None):
        self.name = name
        self.cons = cons.copy()
        self.dtype = dtype
        self.cvars = {}
        self.cvars[name] = svgen_typedef(dtype, name)

    def add_var(self, name, dtype):
        self.cvars[name] = svgen_typedef(dtype, name)


def create_type_cons(dtype, name, cons, **var):
    tcons = SVRandConstraints(name, cons, dtype)
    for name, dtype in var.items():
        tcons.add_var(name, dtype)

    return tcons


def get_svrand_constraint(outdir, cons, seed='random', start_cadence=True):
    base_addr = os.path.dirname(__file__)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(base_addr),
        trim_blocks=True,
        lstrip_blocks=True)
    env.globals.update(zip=zip, int=int, print=print, issubclass=issubclass)

    context = {'tcons': cons}
    res = env.get_template('svrand_top.j2').render(context)
    save_file('svrand_top.sv', outdir, res)

    if start_cadence:
        dpi_path = os.path.abspath(os.path.join(ROOT_DIR, 'sim', 'dpi'))
        ret = os.system(
            f'irun -64bit -incdir {dpi_path} {dpi_path}/sock.sv {dpi_path}/socket_pkg.sv {dpi_path}/sock.c {outdir}/svrand_top.sv -top top +svseed={seed} -define VERBOSITY=3'
        )
        if ret != 0:
            raise SVRandCompileError(f'Constrained random compilation failed.')


class SVRandSocket:
    SVRAND_CONN_NAME = "_svrand"

    def __init__(self, constraints):
        self.constraints = constraints

        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ('localhost', 4567)
        print('starting up on %s port %s' % server_address)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(True)

        self.sock.bind(server_address)

        # Listen for incoming connections
        self.sock.listen(1)

        # def setup(self):
        print("Wait for connection")
        conn, addr = self.sock.accept()

        msg = conn.recv(1024)
        port_name = msg.decode()

        self.conn = conn

        print(f"Connection received for {port_name}")

    def get_rand(self, name):
        data = None
        for i, c in enumerate(self.constraints):
            if c.name == name:
                dtype = c.dtype
                req = i + 1
                break

        # Send request
        pkt = req.to_bytes(4, byteorder='little')
        self.conn.sendall(b'\x01\x00\x00\x00' + pkt)

        # Get random data
        while data is None:
            try:
                buff_size = math.ceil(int(dtype) / 8)
                if buff_size < 4:
                    buff_size = 4
                if buff_size % 4:
                    buff_size += 4 - (buff_size % 4)
                data = self.conn.recv(buff_size)
            except socket.error:
                print('SVRandSocket: socket error on {SVRAND_CONN_NAME}')
        data = u32_bytes_decode(data, dtype)
        return data

    def finish(self):
        print(f"Closing connection for _svrand")
        self.conn.sendall(b'\x00\x00\x00\x00')
        self.conn.close()
        print("Closing socket server")
        self.sock.close()
