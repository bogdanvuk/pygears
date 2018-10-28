import logging
import math
import os
import socket
from subprocess import DEVNULL, Popen

import jinja2

from pygears import registry, bind
from pygears.definitions import ROOT_DIR
from pygears.sim import sim_log
from pygears.sim.extens.rand_base import RandBase
from pygears.sim.modules.sim_socket import SimSocket, u32_bytes_decode
from pygears.svgen.util import svgen_typedef
from pygears.util.fileio import save_file


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


class SVRandSocket(RandBase):
    SVRAND_CONN_NAME = "_svrand"

    def __init__(self, top, cons, run=False, port=4567, **kwds):
        super().__init__(top, cons, **kwds)
        self.run_cosim = run
        self.cosim_pid = None
        kwds['batch'] = True
        kwds['clean'] = True
        self.kwds = kwds
        self.port = port
        self.open_sock = True

    def create_type_cons(self, desc={}):
        tcons = SVRandConstraints(
            name=desc['name'],
            dtype=desc['dtype'],
            cons=desc['cons'],
            cls=desc['cls'],
            cls_params=desc['cls_params'])

        for name, dtype in desc['params'].items():
            tcons.add_var(name, dtype)

        return tcons

    def before_setup(self, sim):
        sim_map = registry('sim/map')
        for module, sim_gear in sim_map.items():
            if isinstance(sim_gear, SimSocket):
                self.open_sock = False

        self.create_svrand_top()

        if self.open_sock:
            self.cosim_pid = None
            if self.run_cosim:
                outdir = registry('sim/artifact_dir')
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
                self.cosim_pid = Popen(
                    [f'./svrand_runsim.sh'] + args.split(' '),
                    stdout=stdout,
                    stderr=stdout,
                    cwd=outdir)
                sim_log().info(f"Cosimulator started")

            self.connect()
        else:
            hooks = {}
            hooks['module_init'] = 'svrand_top rand_i();'
            data_rng = [x for x in range(1, len(self.constraints) + 1)]
            hooks[
                'synchro_req'] = f'if (data inside {{{", ".join(str(x) for x in data_rng)}}}) ret = rand_i.get_rand(synchro_handle, data);'
            bind('sim/config/socket_hooks', hooks)

    def connect(self):
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ('localhost', self.port)
        print('starting up on %s port %s' % server_address)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(server_address)

        if self.cosim_pid:
            self.sock.settimeout(1)
        else:
            self.sock.setblocking(True)

        self.sock.listen(1)

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
            sim_log().info("Wait for connection")
            self.sock.listen(1)
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
                sim_log().error(f'socket error on {self.SYNCHRO_HANDLE_NAME}')
                raise socket.error
        data = u32_bytes_decode(data, dtype)
        return data

    def get_rand(self, name):
        req, dtype = self.parse_name(name)
        data = self.send_req(req, dtype)
        return data

    def at_exit(self, sim):
        if self.open_sock:
            if hasattr(self, 'conn'):
                self.conn.sendall(b'\x00\x00\x00\x00')
                self.conn.close()
                self.sock.close()
                self.open_sock = False

            if self.cosim_pid is not None:
                self.cosim_pid.terminate()

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

        context = {
            'dti_verif_path':
            os.path.abspath(os.path.join(ROOT_DIR, 'sim', 'dpi')),
            'out_path':
            os.path.abspath(self.outdir),
            'includes': [os.path.abspath(os.path.join(self.outdir, '*.sv'))],
            'top_name':
            'svrand_top'
        }

        env.loader = jinja2.FileSystemLoader(
            os.path.join(ROOT_DIR, 'sim', 'modules'))
        res = env.get_template('runsim.j2').render(context)
        fname = save_file('svrand_runsim.sh', self.outdir, res)
        os.chmod(fname, 0o777)
