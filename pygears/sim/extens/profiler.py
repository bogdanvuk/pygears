import cProfile
# from pygears.sim import sim
from pygears.sim.extens.sim_extend import SimExtend


class Profiler(SimExtend):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def before_run(self, sim):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def after_run(self, sim):
        self.pr.disable()
        # s = io.StringIO()
        # ps = pstats.Stats(self.pr, stream=s).sort_stats('time')
        # ps.print_stats()
        self.pr.dump_stats(self.fn)
