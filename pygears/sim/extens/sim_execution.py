from .sim_extend import SimExtend
from pygears.sim import log


class SimExecution(SimExtend):
    # def before_call_forward(self, sim, sim_gear):
    #     return True

    def after_call_forward(self, sim, sim_gear):
        log.info(f'forward')
        return True

    # def before_call_back(self, sim, sim_gear):
    #     return True

    def after_call_back(self, sim, sim_gear):
        log.info(f'back')
        return True
