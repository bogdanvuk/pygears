import math
import os

import jinja2

from pygears import reg
from pygears.typing import Queue, typeof, Tuple, Union, Array, Queue, Integral
from pygears.hdl.templenv import TemplateEnv
from pygears.sim.extens.rand_base import RandBase
from pygears.hdl.sv.util import svgen_typedef
from pygears.util.fileio import save_file
from pygears.conf import inject, Inject
from pygears.sim.extens.svsock import register_intf, CMD_READ


class SVRandConstraints:
    def __init__(self,
                 name='dflt',
                 cons=[],
                 dtype=None,
                 cls='dflt_tcon',
                 cls_params=None,
                 tenv=None):
        self.name = name
        self.cons = cons.copy()
        self.dtype = dtype
        self.cls = cls
        self.cls_params = cls_params
        self.cvars = {}
        self.cvars['dout'] = svgen_typedef(dtype, 'dout')
        self.tenv = tenv

    def add_var(self, name, dtype):
        self.cvars[name] = svgen_typedef(dtype, name)

    def get_class(self):
        return self.tenv.cons.default_tcon(self)


class QueueConstraints(SVRandConstraints):
    def get_class(self):
        queue_struct_cons = []
        queue_size_cons = []
        data_cons = []

        for c in self.cons:
            if 'queue.length' in c:
                queue_size_cons.append(c.replace('queue.length', 'length'))
            elif 'queue.struct' in c:
                queue_struct_cons.append(c.replace('queue.struct', 'struct'))
            else:
                data_cons.append(c.replace(f'dout.data', 'data'))

        self.cons = data_cons
        context = {
            'con': self,
            'sv_dtype': self.cvars['dout'],
            'queue_struct_cons': queue_struct_cons,
            'queue_size_cons': queue_size_cons
        }

        if typeof(self.dtype.data, Integral):
            dt = self.dtype.data
            context[
                'sv_data_dtype'] = f'logic {"signed" if dt.signed else ""} [{dt.width-1}:0]'
        else:
            context['sv_data_dtype'] = f'dout_data_t'

        del self.cvars['dout']

        return self.tenv.cons.queue_tcon(**context)


class SVServerIntf:
    def __init__(self):
        pass

    def read(self):
        return "rand_i.get_rand(synchro_handle, data[15:0]);"


class SVServerModule:
    def __init__(self, outdir, constraints, tenv):
        self.tenv = tenv
        self.outdir = outdir
        self.constraints = constraints

    def declaration(self):
        return 'svrand_top rand_i();'

    def files(self):
        files = [os.path.join(self.outdir, 'svrand_top.sv')]

        # custom classes
        for con in self.constraints:
            if con.cls == 'qenvelope':
                files.append(
                    os.path.join(self.outdir, f'qenvelope_{con.name}.sv'))

        return files


def default_tcon_resolver(desc, tenv):
    tcons = SVRandConstraints(name=desc['name'],
                              dtype=desc['dtype'],
                              cons=desc['cons'],
                              cls=desc['cls'],
                              cls_params=desc['cls_params'],
                              tenv=tenv)

    for name, dtype in desc['params'].items():
        tcons.add_var(name, dtype)

    return tcons


def queue_tcon_resolver(desc, tenv):
    tcons = QueueConstraints(name=desc['name'],
                             dtype=desc['dtype'],
                             cons=desc['cons'],
                             cls=desc['cls'],
                             cls_params=desc['cls_params'],
                             tenv=tenv)

    for name, dtype in desc['params'].items():
        tcons.add_var(name, dtype)

    return tcons


tcon_resolvers = {
    Queue: queue_tcon_resolver,
}


def find_tcon_resolver(desc, tenv):
    for templ in tcon_resolvers:
        if typeof(desc['dtype'], templ):
            return tcon_resolvers[templ](desc, tenv)

    return default_tcon_resolver(desc, tenv)


class SVRandSocket(RandBase):
    @inject
    def __init__(self, top, cons=Inject('sim/svrand/constraints')):
        basedir = os.path.dirname(__file__)
        self.tenv = TemplateEnv(basedir)
        self.tenv.cons = self.tenv.load(basedir, 'svrand_cons.j2').module

        super().__init__(top, cons)

    def create_type_cons(self, desc={}):
        return find_tcon_resolver(desc, self.tenv)

    def before_setup(self, sim):
        basedir = os.path.dirname(__file__)
        tenv = TemplateEnv(basedir)

        self.create_svrand_top()
        register_intf(SVServerModule(self.outdir, self.constraints, tenv))

        for c in self.constraints:
            c.index = register_intf(SVServerIntf())

        self.conn = reg['sim/svsock/server']
        self.send_cmd = self.conn.send_cmd
        self.dtype_recv = self.conn.dtype_recv

    def parse_name(self, name):
        for c in self.constraints:
            if c.name == name:
                return c.index, c.dtype

    def send_req(self, index, dtype):
        self.send_cmd(CMD_READ | index)
        return self.dtype_recv(dtype)

    def get_rand(self, name):
        index, dtype = self.parse_name(name)
        data = self.send_req(index, dtype)
        return data

    def create_svrand_top(self):
        base_addr = os.path.dirname(__file__)
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(base_addr),
                                 trim_blocks=True,
                                 lstrip_blocks=True)

        context = {
            'tcons': self.constraints,
        }

        res = env.get_template('svrand_top.j2').render(context)
        save_file('svrand_top.sv', self.outdir, res)

        # custom classes
        for con in self.constraints:
            if con.cls == 'qenvelope':
                context = {'tcon': con}
                res = env.get_template('qenvelope.j2').render(context)
                save_file(f'qenvelope_{con.name}.sv', self.outdir, res)
