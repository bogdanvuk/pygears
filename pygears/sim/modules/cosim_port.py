from pygears.sim import delta, clk, sim_log, timestep
from pygears import GearDone

class CosimNoData(Exception):
    pass


class InCosimPort:
    def __init__(self, main, port, name=None):
        self.port = port
        self.name = name if name else port.basename
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
                    self.main.reset_in(self.name)
                    # sim_log().info(f'Wait for intf -> {self.name}')
                    data = await intf.pull()
                    # sim_log().info(f'Set {data} -> {self.name}')
                    self.active = True
                    self.main.write_in(self.name, data)
                elif (phase == 'back') and (self.active):
                    if self.main.ready_in(self.name):
                        # sim_log().info(f'Ack {self.name}')
                        self.active = False
                        intf.ack()
                    # else:
                    #     sim_log().info(f'NAck {self.name}')

            except (BrokenPipeError, ConnectionResetError):
                intf.finish()
                raise GearDone

            phase = await delta()


class OutCosimPort:
    def __init__(self, main, port, name=None):
        self.port = port
        self.name = name if name else port.basename
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
                # sim_log().info(f'CosimPort {self.name} finished')
                intf.finish()
                raise GearDone

            try:
                # sim_log().info(f'{self.name} read_out')
                data = self.main.read_out(self.name)
                # sim_log().info(f'Put {data} -> {self.name}')
                await intf.put(data)
                # sim_log().info(f'Ack {data} -> {self.name}')
                self.main.ack_out(self.name)
            except (BrokenPipeError, ConnectionResetError):
                intf.finish()
                raise GearDone
            except CosimNoData:
                pass

            await clk()
