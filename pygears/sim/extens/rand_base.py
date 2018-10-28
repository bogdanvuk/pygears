from pygears import registry, bind
from pygears.sim import sim_log
from pygears.sim.extens.sim_extend import SimExtend
from pygears.typing import Queue


class RandBase(SimExtend):
    def __init__(self, top, cons, **kwds):
        super().__init__()
        self.outdir = registry('sim/artifact_dir')
        self.constraints = self.create_constraints(cons)
        bind('sim/config/randomizator', self)

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

    def create_constraints(self, cons):
        constraints = []
        for c in cons:
            constraints.append(self.create_type_cons(c.get_data_desc()))
            if c.is_queue:
                constraints.append(self.create_type_cons(c.get_eot_desc()))
        return constraints

    def create_type_cons(self, desc={}):
        sim_log().error('Create type constraints function not implemented.')

    def get_rand(self, name):
        sim_log().error('Get rand function not implemented.')
