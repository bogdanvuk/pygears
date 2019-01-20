from pygears.sim.sim_gear import SimGear
from pygears.sim import delta, timestep, sim_log, clk
from pygears.conf import Inject, reg_inject
from pygears import GearDone
from .cosim_port import CosimNoData, InCosimPort, OutCosimPort


class CosimBase(SimGear):
    SYNCHRO_HANDLE_NAME = "_synchro"

    @reg_inject
    def __init__(self, gear, timeout=-1, sim_map=Inject('sim/map')):
        super().__init__(gear)
        self.timeout = timeout
        self.in_cosim_ports = [InCosimPort(self, p) for p in gear.in_ports]
        self.out_cosim_ports = [OutCosimPort(self, p) for p in gear.out_ports]

        for p in (self.in_cosim_ports + self.out_cosim_ports):
            sim_map[p.port] = p

    def setup(self):
        for p in (self.in_cosim_ports + self.out_cosim_ports):
            p.cosim_intf = self.handlers[p.port.basename]

        super().setup()

    def _forward(self):

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
            if intf.ready_nb():
                try:
                    hout = self.handlers[p.basename]
                    intf.put_nb(hout.read())
                    # print(f'Put {hout.read()} -> {p.basename}')
                    self.dout_put.add(p)
                    self.activity_monitor = 0
                except CosimNoData:
                    pass

    def _back(self):
        for p in self.dout_put.copy():
            intf = p.producer
            hout = self.handlers[p.basename]
            if intf.ready_nb():
                # print(f'Put ACK -> {p.basename}')
                hout.ack()
                self.dout_put.remove(p)
            else:
                hout.reset()

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

    def read_out(self, port):
        if self.cur_cycle_data_not_forward:
            self.handlers[self.SYNCHRO_HANDLE_NAME].forward()
            self.cur_cycle_data_not_forward = False

        hout = self.handlers[port.basename]
        hout.reset()
        return hout.read()

    def ack_out(self, port):
        self.cur_cycle_data_not_back = True
        hout = self.handlers[port.basename]
        hout.ack()
        self.activity_monitor = 0

    def write_in(self, port, data):
        self.cur_cycle_data_not_forward = True

        hin = self.handlers[port.basename]
        return hin.send(data)

    def reset_in(self, port):
        self.cur_cycle_data_not_forward = True

        hin = self.handlers[port.basename]
        hin.reset()

    def ready_in(self, port):
        if self.cur_cycle_data_not_back:
            self.handlers[self.SYNCHRO_HANDLE_NAME].back()
            self.cur_cycle_data_not_back = False

        hin = self.handlers[port.basename]
        if hin.ready():
            self.activity_monitor = 0
            return True
        else:
            return False

    async def func(self, *args, **kwds):
        self.activity_monitor = 0
        self.din_pulled = set()
        self.dout_put = set()
        self.prev_timestep = -1

        try:
            # phase = 'forward'

            while True:
                # if phase == 'forward':
                #     # self._forward()
                #     self.handlers[self.SYNCHRO_HANDLE_NAME].forward()
                # elif phase == 'back':
                #     self._back()
                #     self.handlers[self.SYNCHRO_HANDLE_NAME].back()
                # elif phase == 'cycle':

                self.cur_cycle_data_not_forward = True
                self.cur_cycle_data_not_back = True

                # if self.prev_timestep != timestep():
                # sim_log().info(f'Activity monitor: {self.activity_monitor}')
                #     self.prev_timestep = timestep()
                if self.activity_monitor == self.timeout:
                    raise GearDone

                self.handlers[self.SYNCHRO_HANDLE_NAME].cycle()
                self.activity_monitor += 1

                # sim_log().info(f'Waiting for a clock')

                phase = None
                while phase != 'cycle':
                    phase = await delta()

                if self.cur_cycle_data_not_forward:
                    self.handlers[self.SYNCHRO_HANDLE_NAME].forward()

                if self.cur_cycle_data_not_back:
                    self.handlers[self.SYNCHRO_HANDLE_NAME].back()

                # sim_log().info(f'Cycle')

                # phase = await delta()

        except GearDone as e:
            # print(f"SimGear canceling: {self.gear.name}")
            for p in self.gear.out_ports:
                p.producer.finish()

            self._finish()
            raise e
