from pygears import reg
from pygears.sim import log
from pygears.sim.extens.sim_extend import SimExtend
from pygears.typing import Queue
from pygears.conf import inject, Inject


class RandBase(SimExtend):
    @inject
    def __init__(self, cons, outdir=Inject('results-dir')):
        super().__init__()
        self.outdir = outdir
        self.constraints = self.randomizes(cons)
        reg['sim/config/randomizer'] = self

    def get_dtype_by_name(self, name):
        for constraint in self.constraints:
            if constraint.name == name:
                return constraint.dtype

        # check if queue
        data = None
        eot = None
        for constraint in self.constraints:
            if constraint.name == f'{name}_data':
                data = constraint.dtype
            if constraint.name == f'{name}_eot':
                eot = constraint.dtype

        if data and eot:
            return Queue[data, len(eot)]

    def randomizes(self, cons):
        constraints = []
        for c in cons:
            constraints.append(self.create_type_cons(c.get_data_desc()))
            if c.is_queue:
                constraints.append(self.create_type_cons(c.get_eot_desc()))
        return constraints

    def create_type_cons(self, desc={}):
        log.error('Create type constraints function not implemented.')

    def get_rand(self, name):
        log.error('Get rand function not implemented.')
