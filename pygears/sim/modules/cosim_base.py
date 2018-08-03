from pygears.sim.sim_gear import SimGear
from pygears.sim import clk, timestep, delta
from pygears import GearDone, module
import time


class CosimNoData(Exception):
    pass


class CosimBase(SimGear):
    SYNCHRO_HANDLE_NAME = "_synchro"

    def __init__(self, gear, timeout=-1):
        super().__init__(gear)
        self.timeout = timeout

    def finish(self):
        super().finish()

    async def func(self, *args, **kwds):
        activity_monitor = 0
        din_pulled = set()
        dout_put = set()
        try:
            while True:
                activity_monitor += 1
                if activity_monitor == self.timeout:
                    raise GearDone

                self.handlers[self.SYNCHRO_HANDLE_NAME].cycle()

                for p in self.gear.in_ports:
                    intf = p.consumer
                    if p.basename not in self.handlers:
                        continue

                    hin = self.handlers[p.basename]

                    if intf.done():
                        hin.close()
                        del self.handlers[p.basename]

                    if p not in din_pulled:
                        if not intf.empty():
                            data = intf.pull_nb()
                            din_pulled.add(p)
                            hin.send(data)
                        else:
                            hin.reset()

                self.handlers[self.SYNCHRO_HANDLE_NAME].forward()

                for p in self.gear.out_ports:
                    intf = p.producer
                    if intf.ready_nb():
                        hout = self.handlers[p.basename]
                        try:
                            intf.put_nb(hout.read())
                            dout_put.add(p)
                            activity_monitor = 0
                        except CosimNoData:
                            pass
                    else:
                        hout.reset()

                await delta()

                for p in dout_put.copy():
                    intf = p.producer
                    if intf.ready_nb():
                        hout = self.handlers[p.basename]
                        hout.ack()
                        dout_put.remove(p)

                self.handlers[self.SYNCHRO_HANDLE_NAME].back()

                for p in din_pulled.copy():
                    if p.basename not in self.handlers:
                        continue

                    hin = self.handlers[p.basename]
                    if hin.ready():
                        activity_monitor = 0
                        din_pulled.remove(p)
                        intf = p.consumer
                        intf.ack()

                await clk()

        except GearDone as e:
            # print(f"SimGear canceling: {self.gear.name}")
            for p in self.gear.out_ports:
                p.producer.finish()

            self.finish()
            raise e
