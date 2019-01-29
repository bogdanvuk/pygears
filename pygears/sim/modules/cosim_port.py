from pygears.sim import delta, clk, sim_log, timestep
from pygears import GearDone

class CosimNoData(Exception):
    pass


class InCosimPort:
    def __init__(self, main, port):
        self.port = port
        self.done = False
        self.main = main

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
        self.active = False

        while True:
            if self.main.done:
                intf.finish()
                raise GearDone

            try:
                if (phase == 'forward') and (not self.active):
                    self.main.reset_in(self.port)
                    # print(f'Wait for intf -> {self.port.basename}')
                    data = await intf.pull()
                    # print(f'Set {data} -> {self.port.basename}')
                    self.active = True
                    self.main.write_in(self.port, data)
                elif (phase == 'back') and (self.active):
                    if self.main.ready_in(self.port):
                        # print(f'Ack {self.port.basename}')
                        self.active = False
                        intf.ack()
            except (BrokenPipeError, ConnectionResetError):
                intf.finish()
                raise GearDone

            phase = await delta()


class OutCosimPort:
    def __init__(self, main, port):
        self.port = port
        self.done = False
        self.main = main

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
                # print(f'{self.port.basename} read_out')
                data = self.main.read_out(self.port)
                # print(f'Put {data} -> {self.port.basename}')
                await intf.put(data)
                # print(f'Ack {data} -> {self.port.basename}')
                self.main.ack_out(self.port)
            except (BrokenPipeError, ConnectionResetError):
                intf.finish()
                raise GearDone
            except CosimNoData:
                pass

            await clk()
