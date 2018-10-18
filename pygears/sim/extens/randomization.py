from itertools import islice

from pygears import registry
from pygears.core.util import perpetum
from pygears.sim import sim_log
from pygears.sim.extens.scvrand import SCVRand
from pygears.sim.extens.svrand import SVRandSocket
from pygears.typing import Queue
from pygears.typing.queue import QueueMeta


def get_rand(name, cnt=None):
    randomizator = registry('sim/config/randomizator')

    if isinstance(randomizator, SVRandSocket):
        if randomizator.open_sock:
            rand_func = perpetum(randomizator.get_rand, name)
        else:
            req, dtype = randomizator.parse_name(name)
            simsoc = registry('sim/config/socket')
            rand_func = perpetum(simsoc.send_req, req, dtype)
    elif isinstance(randomizator, SCVRand):
        rand_func = perpetum(randomizator.get_rand, name)
    else:
        sim_log().error('Randomizator not set')
        return None

    if cnt is not None:
        yield from islice(rand_func, cnt)
    else:
        yield from rand_func


def rand_seq(name, cnt=None):
    randomizator = registry('sim/config/randomizator')
    dtype = randomizator.get_dtype_by_name(name)

    if isinstance(dtype, Queue) or isinstance(dtype, QueueMeta):
        rnd_data = get_rand(f'{name}_data')
        rnd_eot = get_rand(f'{name}_eot')
        tout = None
        while cnt != 0:
            eot = next(rnd_eot)
            data = next(rnd_data)
            if tout is None:
                tout = Queue[type(data), len(eot)]

            yield tout((data, *eot))
            if cnt is not None:
                if eot == int('1' * len(eot), 2):
                    cnt -= 1
    else:
        yield from get_rand(name, cnt)


class ConstraintWrap:
    def __init__(self,
                 dtype,
                 name,
                 cons=[],
                 params={},
                 cls='dflt_tcon',
                 cls_params=None,
                 eot_cons=[],
                 eot_cls='qenvelope',
                 eot_cls_params=None,
                 eot_params={}):
        self.dtype = dtype
        self.name = name

        self.cons = cons
        self.params = params
        self.cls = cls
        self.cls_params = cls_params

        self.is_queue = False
        if isinstance(dtype, Queue) or isinstance(dtype, QueueMeta):
            self.is_queue = True
            self.eot_cons = eot_cons
            self.eot_params = eot_params
            self.eot_cls = eot_cls
            self.eot_cls_params = eot_cls_params

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


def create_constraint(dtype,
                      name,
                      cons=[],
                      params={},
                      cls='dflt_tcon',
                      cls_params=None,
                      eot_cons=[],
                      eot_cls='qenvelope',
                      eot_cls_params=None,
                      eot_params={}):
    return ConstraintWrap(**locals())
