from pygears.sim import delta, clk, sim_log, timestep
from pygears import GearDone

class CosimNoData(Exception):
    pass


class InCosimPort:
    def __init__(self, main, port):
        self.port = port
        self.done = False
        self.main = main
        # self.cosim_intf = cosim_intf

    @property
    def gear(self):
        return self.port.gear

    @property
    def in_ports(self):
        return [self.port]

    @property
    def out_ports(self):
        return []

    def setup(self):
        pass

    async def run(self):
        intf = self.port.consumer

        phase = 'forward'

        while True:
            if self.main.done:
                raise GearDone

            if phase == 'forward':
                self.main.reset_in(self.port)
                # print(f'Wait for intf -> {self.port.basename}')
                data = await intf.pull()
                # print(f'Set {data} -> {self.port.basename}')
                self.main.write_in(self.port, data)
            elif phase == 'back':
                if self.main.ready_in(self.port):
                    # print(f'Ack {self.port.basename}')
                    intf.ack()

            phase = await delta()


class OutCosimPort:
    def __init__(self, main, port):
        self.port = port
        self.done = False
        self.main = main
        # self.cosim_intf = cosim_intf

    @property
    def gear(self):
        return self.port.gear

    @property
    def in_ports(self):
        return []

    @property
    def out_ports(self):
        return [self.port]

    def setup(self):
        pass

    async def run(self):
        intf = self.port.producer

        while True:
            if self.main.done:
                # sim_log().info(f'CosimPort {self.port.name} finished')
                intf.finish()
                raise GearDone

            try:
                data = self.main.read_out(self.port)
                # print(f'Put {data} -> {self.port.basename}')
                await intf.put(data)
                # print(f'Ack {data} -> {self.port.basename}')
                self.main.ack_out(self.port)
            except CosimNoData:
                pass

            await clk()
