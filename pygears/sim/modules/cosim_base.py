from pygears.sim.sim_gear import SimGear
from pygears.sim import delta
from pygears import GearDone


class CosimNoData(Exception):
    pass


class CosimBase(SimGear):
    SYNCHRO_HANDLE_NAME = "_synchro"

    def __init__(self, gear, timeout=-1):
        super().__init__(gear)
        self.timeout = timeout

    def _forward(self):
        self.handlers[self.SYNCHRO_HANDLE_NAME].cycle()

        for p in self.gear.in_ports:
            intf = p.consumer
            if p.basename not in self.handlers:
                continue

            hin = self.handlers[p.basename]

            if intf.done:
                hin.close()
                del self.handlers[p.basename]

            if p not in self.din_pulled:
                if not intf.empty():
                    data = intf.pull_nb()
                    self.din_pulled.add(p)
                    hin.send(data)
                else:
                    hin.reset()

        self.handlers[self.SYNCHRO_HANDLE_NAME].forward()

        for p in self.gear.out_ports:
            intf = p.producer
            hout = self.handlers[p.basename]
            if intf.ready_nb():
                try:
                    intf.put_nb(hout.read())
                    self.dout_put.add(p)
                    self.activity_monitor = 0
                except CosimNoData:
                    pass
            else:
                hout.reset()

    def _back(self):
        for p in self.dout_put.copy():
            intf = p.producer
            if intf.ready_nb():
                hout = self.handlers[p.basename]
                hout.ack()
                self.dout_put.remove(p)

        self.handlers[self.SYNCHRO_HANDLE_NAME].back()

        for p in self.din_pulled.copy():
            if p.basename not in self.handlers:
                continue

            hin = self.handlers[p.basename]
            if hin.ready():
                self.activity_monitor = 0
                self.din_pulled.remove(p)
                intf = p.consumer
                intf.ack()

    async def func(self, *args, **kwds):
        self.activity_monitor = 0
        self.din_pulled = set()
        self.dout_put = set()
        try:
            phase = 'forward'

            while True:
                if phase == 'forward':
                    self.activity_monitor += 1
                    self._forward()
                else:
                    self._back()

                if self.activity_monitor == self.timeout:
                    raise GearDone
                else:
                    phase = await delta()

        except GearDone as e:
            # print(f"SimGear canceling: {self.gear.name}")
            for p in self.gear.out_ports:
                p.producer.finish()

            self._finish()
            raise e
