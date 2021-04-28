import time
import cProfile, pstats, io
from pygears import gear
from pygears.typing import Uint
from pygears.lib.verif import drv
# from pygears.sim import sim
from pygears.sim.extens.sim_extend import SimExtend
from pygears.lib import shred


class Profiler(SimExtend):
    def before_run(self, sim):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def after_run(self, sim):
        self.pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(self.pr, stream=s).sort_stats('time')
        ps.print_stats()
        ps.dump_stats('/tmp/pygears.profile')
        print(s.getvalue())


@gear
async def passthrough(din: Uint[16]) -> Uint[16]:
    async with din as d:
        yield d


# d = drv(t=Uint[16], seq=list(range(4000)))

# for _ in range(20):
#     d = d | passthrough

# d | shred

# t = time.time()
# # sim(extens=[Profiler])
# sim()
# print("%.3f" % (time.time()-t))
