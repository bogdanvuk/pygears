from .sim_extend import SimExtend
from pygears.sim import sim_log


class SimExecution(SimExtend):
    # def before_call_forward(self, sim, sim_gear):
    #     return True

    def after_call_forward(self, sim, sim_gear):
        sim_log().info(f'forward')
        return True

    # def before_call_back(self, sim, sim_gear):
    #     return True

    def after_call_back(self, sim, sim_gear):
        sim_log().info(f'back')
        return True
