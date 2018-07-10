import math
import os
import socket

import jinja2

from pygears import registry
from pygears.sim.modules.sim_socket import u32_bytes_decode
from pygears.svgen.util import svgen_typedef
from pygears.util.fileio import save_file

from pygears.sim.modules.sim_socket import SimSocket


def get_rand_data(name):
    # print(f'Getting random data for {name}')
    svrand = registry('SimConfig')['SVRandSocket']
    if svrand.open_sock:
        data = svrand.get_rand(name)
    else:
        req, dtype = svrand.parse_name(name)
        simsoc = registry('SimConfig')['SimSocket']
        data = simsoc.send_req(req, dtype)
    return data


class SVRandError(Exception):
    pass


class SVRandConstraints:
    def __init__(self,
                 name='dflt',
                 cons=[],
                 dtype=None,
                 cls='dflt_tcon',
                 cls_params=None):
        self.name = name
        self.cons = cons.copy()
        self.dtype = dtype
        self.cls = cls
        self.cls_params = cls_params
        self.cvars = {}
        self.cvars[name] = svgen_typedef(dtype, name)

    def add_var(self, name, dtype):
        self.cvars[name] = svgen_typedef(dtype, name)


def create_type_cons(dtype,
                     name,
                     cons,
                     cls='dflt_tcon',
                     cls_params=None,
                     **var):
    tcons = SVRandConstraints(
        name=name, cons=cons, dtype=dtype, cls=cls, cls_params=cls_params)
    for name, dtype in var.items():
        tcons.add_var(name, dtype)

    return tcons


class SVRandSocket:
    SVRAND_CONN_NAME = "_svrand"

    def __init__(self, top, conf):
        self.outdir = conf['outdir']

        try:
            self.constraints = conf['constraints']
        except KeyError:
            raise SVRandError(f'No constraints passed to init')

        if 'rand_port' in conf:
            self.port = conf['rand_port']
        else:
            self.port = 4567

        self.open_sock = True
        sim = registry('Simulator')
        sim.events['before_setup'].append(self.before_setup)
        sim.events['after_run'].append(self.after_run)
        registry('SimConfig')['SVRandSocket'] = self

    def before_setup(self, sim):
        sim_map = registry('SimMap')
        for module, sim_gear in sim_map.items():
            if isinstance(sim_gear, SimSocket):
                self.open_sock = False

        self.create_svrand_top()

        if self.open_sock:
            self.connect()
        else:
            hooks = {}
            hooks['module_init'] = 'svrand_top rand_i();'
            data_rng = [x for x in range(1, len(self.constraints) + 1)]
            hooks[
                'synchro_req'] = f'if (data inside {{{", ".join(str(x) for x in data_rng)}}}) ret = rand_i.get_rand(synchro_handle, data);'
            registry('SimConfig')['SimSocketHooks'] = hooks

    def connect(self):
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ('localhost', self.port)
        print('starting up on %s port %s' % server_address)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(True)

        self.sock.bind(server_address)

        # Listen for incoming connections
        self.sock.listen(1)

        print("Wait for connection")
        conn, addr = self.sock.accept()

        msg = conn.recv(1024)
        port_name = msg.decode()

        self.conn = conn

        print(f"Connection received for {port_name}")

    def parse_name(self, name):
        for i, c in enumerate(self.constraints):
            if c.name == name:
                dtype = c.dtype
                req = i + 1
                break
        return req, dtype

    def send_req(self, req, dtype):
        data = None

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

    def get_rand(self, name):
        req, dtype = self.parse_name(name)
        data = self.send_req(req, dtype)
        return data

    def after_run(self, sim):
        if self.open_sock:
            print(f"Closing connection for _svrand")
            self.conn.sendall(b'\x00\x00\x00\x00')
            self.conn.close()
            print("Closing socket server")
            self.sock.close()

    def create_svrand_top(self):
        base_addr = os.path.dirname(__file__)
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(base_addr),
            trim_blocks=True,
            lstrip_blocks=True)
        env.globals.update(
            zip=zip, int=int, print=print, issubclass=issubclass)

        context = {
            'tcons': self.constraints,
            'open_sock': self.open_sock,
            'port': self.port
        }
        res = env.get_template('svrand_top.j2').render(context)
        save_file('svrand_top.sv', self.outdir, res)

        # custom classes
        for con in self.constraints:
            if con.cls == 'qenvelope':
                context = {'tcon': con}
                res = env.get_template('qenvelope.j2').render(context)
                save_file(f'qenvelope_{con.name}.sv', self.outdir, res)
