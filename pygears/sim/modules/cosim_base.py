from dataclasses import dataclass
from pygears.sim.sim_gear import SimGear
from pygears.sim import delta, timestep, log, clk
from pygears.sim.sim import SimPlugin
from pygears.conf import Inject, inject
from pygears import GearDone, reg
from .cosim_port import CosimNoData, InCosimPort, OutCosimPort


class CosimBase(SimGear):
    @inject
    def __init__(self, gear, timeout=-1, sim_map=Inject('sim/map')):
        super().__init__(gear)
        self.timeout = timeout
        self.in_cosim_ports = [InCosimPort(self, p) for p in gear.in_ports]
        self.out_cosim_ports = [OutCosimPort(self, p) for p in gear.out_ports]
        self.eval_needed = False

        for p in (self.in_cosim_ports + self.out_cosim_ports):
            sim_map[p.port] = p

    def cycle(self):
        raise NotImplementedError()

    def forward(self):
        raise NotImplementedError()

    def back(self):
        raise NotImplementedError()

    def read_out(self, port):
        if not port in self.handlers:
            raise ConnectionResetError

        if self.eval_needed:
            self.forward()

        self.eval_needed = True

        hout = self.handlers[port]
        hout.reset()
        return hout.read()

    def ack_out(self, port):
        if not port in self.handlers:
            raise ConnectionResetError

        self.eval_needed = True
        hout = self.handlers[port]
        hout.ack()
        self.activity_monitor = 0

    def write_in(self, port, data):
        if not port in self.handlers:
            raise ConnectionResetError

        self.eval_needed = True

        hin = self.handlers[port]
        return hin.send(data)

    def reset_in(self, port):
        if not port in self.handlers:
            raise ConnectionResetError

        self.eval_needed = True

        hin = self.handlers[port]
        hin.reset()

    def ready_in(self, port):
        if not port in self.handlers:
            raise ConnectionResetError

        if self.eval_needed:
            self.back()
            self.eval_needed = False

        hin = self.handlers[port]
        if hin.ready():
            self.activity_monitor = 0
            return True
        else:
            return False

    async def func(self, *args, **kwds):
        self.activity_monitor = 0
        self.eval_needed = False

        try:
            while True:

                phase = None
                while phase != 'back':
                    phase = await delta()

                if self.eval_needed:
                    self.forward()
                    self.eval_needed = False

                if self.activity_monitor == self.timeout:
                    raise GearDone

                self.cycle()
                self.activity_monitor += 1

        except (GearDone, BrokenPipeError):
            # print(f"SimGear canceling: {self.gear.name}")
            for p in self.gear.out_ports:
                p.producer.finish()

            self._finish()
            raise GearDone


@dataclass
class AuxClock:
    name: str
    frequency: int


class CosimPlugin(SimPlugin):
    @classmethod
    def bind(cls):
        reg.confdef('sim/aux_clock', default=[])
