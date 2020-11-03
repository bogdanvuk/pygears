from pygears.sim import SimPlugin

from itertools import islice

from pygears import reg
from pygears.core.util import perpetum
from pygears.sim import log
from pygears.sim.extens.scvrand import SCVRand
from pygears.sim.extens.svrand import SVRandSocket
from pygears.typing import Queue, typeof, Bool, Tuple, Uint
from pygears.typing.queue import QueueMeta


def register_exten():
    if SVRandSocket not in reg['sim/extens']:
        reg['sim/extens'].append(SVRandSocket)
        if reg['sim/simulator'] is not None:
            SVRandSocket(top=None)


def get_rand(name, cnt=None, rand_func=None):
    if rand_func is None:
        randomizer = reg['sim/config/randomizer']
        rand_func = perpetum(randomizer.get_rand, name)

    if cnt is not None:
        yield from islice(rand_func, cnt)
    else:
        yield from rand_func


def queue_rand_seq(dtype, name):
    randomizer = reg['sim/config/randomizer']

    while True:
        val = randomizer.get_rand(name)
        yield val

        if val.eot == dtype.eot.max:
            break


def rand_seq(name, cnt=None):
    randomizer = reg['sim/config/randomizer']
    dtype = randomizer.get_dtype_by_name(name)

    if typeof(dtype, Queue):
        yield from get_rand(name, cnt, perpetum(queue_rand_seq, dtype, name))
    else:
        yield from get_rand(name, cnt)


class ConstraintWrap:
    def __init__(
            self,
            dtype,
            name,
            cons=[],
            cnt=None,
            params={},
            cls='dflt_tcon',
            cls_params=None):
        self.dtype = dtype
        self.name = name

        self.cons = cons
        self.params = params
        self.cls = cls
        self.cls_params = cls_params
        self.is_queue = False

    def get_data_desc(self):
        return {
            'name': self.name if not self.is_queue else f'{self.name}_data',
            'dtype': self.dtype if not self.is_queue else self.dtype[0],
            'cons': self.cons,
            'params': self.params,
            'cls': self.cls,
            'cls_params': self.cls_params
        }

    def get_eot_desc(self):
        return {
            'name': f'{self.name}_eot',
            'dtype': self.dtype.eot,
            'cons': self.eot_cons,
            'params': self.eot_params,
            'cls': self.eot_cls,
            'cls_params': self.eot_cls_params
        }


def randomize(
        dtype,
        name,
        cnt=None,
        cons=None,
        params=None,
        cls='dflt_tcon',
        cls_params=None):

    if cons is None:
        cons = []

    if params is None:
        params = {}

    register_exten()
    cons = ConstraintWrap(**locals())
    reg['sim/svrand/constraints'].append(cons)
    return rand_seq(name, cnt=cnt)


class SVRandPlugin(SimPlugin):
    @classmethod
    def bind(cls):
        reg['sim/svrand/constraints'] = []
        # reg['sim/svsock/server'] = None
