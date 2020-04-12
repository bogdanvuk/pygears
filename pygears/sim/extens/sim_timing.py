from .sim_extend import SimExtend
import time


class SimTiming(SimExtend):
    def __init__(self, window=1000):
        super().__init__()
        self.window = window
        self.forward_times = {}
        self.back_times = {}
        self.total_forward_times = {}
        self.total_back_times = {}

    def before_run(self, sim):
        for sim_gear in sim.sim_gears:
            self.forward_times[sim_gear] = 0
            self.back_times[sim_gear] = 0
            self.total_forward_times[sim_gear] = 0
            self.total_back_times[sim_gear] = 0

    def before_timestep(self, sim, timestep):
        if (timestep % self.window) == 0:
            if timestep > 0:
                print(
                    f"-------------------- {timestep} ----------------------")

                sort = sorted(
                    ((sim_gear, self.forward_times[sim_gear],
                      self.back_times[sim_gear])
                     for sim_gear in sim.sim_gears),
                    key=lambda x: x[1] + x[2])

                print(
                    f'{"name":60} | {"total [ms]":10} | {"forward [us]":12} | {"back [us]":9}')
                print("-" * 100)
                for sim_gear, ft, bt in reversed(sort):
                    forward = int(ft / self.window * 1000000)
                    back = int(bt / self.window * 1000000)
                    total = int((self.total_forward_times[sim_gear] +
                                 self.total_back_times[sim_gear]) * 1000)
                    print(
                        f'{sim_gear.gear.name:60} | {total:10} | {forward:12} | {back:9}'
                    )
                print("-" * 100)

            for sim_gear in sim.sim_gears:
                self.forward_times[sim_gear] = 0
                self.back_times[sim_gear] = 0

        return True

    def before_call_forward(self, sim, sim_gear):
        self.start_time = time.time()
        return True

    def after_call_forward(self, sim, sim_gear):
        delta = time.time() - self.start_time
        self.forward_times[sim_gear] += delta
        self.total_forward_times[sim_gear] += delta
        return True

    def before_call_back(self, sim, sim_gear):
        self.start_time = time.time()
        return True

    def after_call_back(self, sim, sim_gear):
        delta = time.time() - self.start_time
        self.back_times[sim_gear] += delta
        self.total_back_times[sim_gear] += delta
        return True
