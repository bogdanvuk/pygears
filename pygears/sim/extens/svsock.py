import time
import atexit
import tempfile
from math import ceil
import jinja2
import array
import math
import os
import socket
import logging
from pygears.definitions import ROOT_DIR
from subprocess import DEVNULL, Popen
from pygears import reg
from pygears.sim.extens.sim_extend import SimExtend
from pygears.sim import SimPlugin
from pygears.util.fileio import save_file
from pygears.sim import log

from pygears.conf import inject, Inject

CMD_SYS_RESET = 0x80000000
CMD_SET_DATA = 0x40000000
CMD_RESET = 0x20000000
CMD_FORWARD = 0x10000000
CMD_CYCLE = 0x08000000
CMD_READ = 0x04000000
CMD_ACK = 0x02000000
CMD_FINISH = 0x01000000


class CosimulatorStartError(Exception):
    pass


class CosimulatorUnavailable(Exception):
    pass


def register_exten():
    if SVSock not in reg['sim/extens']:
        reg['sim/extens'].append(SVSock)
        if reg['sim/simulator'] is not None:
            SVSock(top=None)


@inject
def register_intf(desc, intfs=Inject('sim/svsock/intfs')):
    register_exten()
    intfs.append(desc)
    return len(intfs) - 1


def u32_repr_gen(data, dtype):
    for i in range(ceil(dtype.width / 32)):
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
    return dtype.decode(u32_bytes_to_int(data) & ((1 << dtype.width) - 1))


class SVSock(SimExtend):
    @inject
    def __init__(self, run=Inject('sim/svsock/run'), **kwds):
        reg['sim/svsock/server'] = self
        self.run_cosim = run
        self.kwds = kwds
        self.sock = None
        self.conn = None
        self.cosim_pid = None
        super().__init__()
        atexit.register(self.finish)

    @property
    @inject
    def outdir(self, outdir=Inject('results-dir')):
        return os.path.join(outdir, 'svsock')

    @inject
    def build(self, intfs=Inject('sim/svsock/intfs')):

        base_addr = os.path.dirname(__file__)
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(base_addr),
                                 trim_blocks=True,
                                 lstrip_blocks=True)
        env.globals.update(zip=zip,
                           int=int,
                           print=print,
                           issubclass=issubclass)

        context = {'port': self.port}
        for phase in [
                'declaration', 'init', 'set_data', 'read', 'ack', 'reset',
                'sys_reset'
        ]:
            context[phase] = {}
            for i, intf in enumerate(intfs):
                if not hasattr(intf, phase):
                    continue

                phase_sv = getattr(intf, phase)()

                if phase_sv is not None:
                    context[phase][i] = phase_sv

        res = env.get_template('svsock_top.j2').render(context)
        save_file('_top.sv', self.outdir, res)

    def sendall(self, pkt):
        self.conn.sendall(pkt)

    def send_cmd(self, req):
        pkt = req.to_bytes(4, byteorder='little')
        self.conn.sendall(pkt)

    def recv(self, size):
        return self.conn.recv(size)

    def dtype_send(self, data, dtype):
        pkt = u32_repr(data, dtype).tobytes()
        self.sendall(pkt)

    def dtype_recv(self, dtype):
        buff_size = math.ceil(dtype.width / 8)
        if buff_size < 4:
            buff_size = 4
        if buff_size % 4:
            buff_size += 4 - (buff_size % 4)

        data = self.recv(buff_size)
        return u32_bytes_decode(data, dtype)

    @inject
    def invoke_cosim(self, intfs=Inject('sim/svsock/intfs')):
        dpi_path = os.path.abspath(os.path.join(ROOT_DIR, 'sim', 'dpi'))

        context = {}
        context['files'] = [os.path.join(dpi_path, 'sock.sv')]
        context['includes'] = []

        for param in ['files', 'includes']:
            for i, intf in enumerate(intfs):
                if not hasattr(intf, param):
                    continue

                param_val = getattr(intf, param)()

                if param_val is not None:
                    context[param].extend(param_val)

        context['includes'].extend([dpi_path, self.outdir])
        context['files'].extend([os.path.join(self.outdir, '_top.sv')])

        if not reg['sim/svsock/backend']:
            raise CosimulatorStartError('No registered cosimulators')

        cosim_pid = None
        for b in reg['sim/svsock/backend'].values():
            try:
                cosim_pid = b(outdir=self.outdir,
                              files=context['files'],
                              includes=context['includes'],
                              makefile=not self.run_cosim)
            except CosimulatorUnavailable:
                pass
            else:
                break
        else:
            raise CosimulatorStartError(
                f'No available cosimulator executables found for any of the plugins: '
                f'{",".join(reg["sim/svsock/backend"].keys())}')

        return cosim_pid

    def before_run(self, sim):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        if self.run_cosim:
            import uuid
            filename = str(uuid.uuid4())
        else:
            filename = "svsock.s"

        self.port = os.path.join(tempfile.gettempdir(), filename)

        if os.path.exists(self.port):
            os.remove(self.port)
        self.sock.bind(self.port)

        # Listen for incoming connections
        # self.sock.listen(len(self.gear.in_ports) + len(self.gear.out_ports))
        self.sock.listen(1)

        self.build()

        # if self.rebuild:
        #     self.build()
        # else:
        #     self.kwds['nobuild'] = True

        if not self.run_cosim:
            self.invoke_cosim()
            self.conn, addr = self.sock.accept()
        else:
            self.sock.settimeout(5)

            self.cosim_pid = self.invoke_cosim()

            ret = None
            while ret is None:
                try:
                    self.conn, addr = self.sock.accept()
                    break
                except socket.timeout:
                    ret = self.cosim_pid.poll()
                    if ret is not None:
                        log.error(
                            f'Cosimulator error: {ret}. Check log File "{self.outdir}/log.log"'
                        )
                        raise CosimulatorStartError

        msg = self.conn.recv(1024)
        port_name = msg.decode()

        log.debug(f"Connection received for {port_name}")

    def finish(self):
        if self.sock:
            if self.conn:
                try:
                    self.send_cmd(CMD_FINISH)
                    time.sleep(0.5)
                except BrokenPipeError:
                    pass

            log.info(f'Done. Closing the socket...')
            self.sock.close()
            time.sleep(1)

            if self.cosim_pid is not None:
                self.cosim_pid.terminate()

            self.sock = None
            self.cosim_pid = None
            self.conn = None
            atexit.unregister(self.finish)

    def after_cleanup(self, sim):
        self.finish()


class SVSockPlugin(SimPlugin):
    @classmethod
    def bind(cls):
        reg.confdef('sim/svsock/backend', default={})
        reg.confdef('sim/svsock/run', default=True)
        reg['sim/svsock/intfs'] = []
        reg['sim/svsock/server'] = None
