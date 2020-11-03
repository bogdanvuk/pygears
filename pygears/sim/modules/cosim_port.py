from pygears.sim import clk, delta, log
from pygears import GearDone


class CosimNoData(Exception):
    pass


class InCosimPort:
    def __init__(self, main, port, name=None):
        self.port = port
        self.name = name if name else port.basename
        self.done = False
        self.parent = None
        self.child = None
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

        self.active = False

        while True:
            if self.main.done:
                intf.finish()
                raise GearDone

            try:
                if self.phase == 'forward':
                    if not self.active:
                        self.main.reset_in(self.name)
                        # log.info(f'Wait for intf -> {self.name}')
                        data = await intf.pull()
                        # log.info(f'Set {data} -> {self.name}')
                        self.active = True
                        self.main.write_in(self.name, data)

                    await delta()
                elif self.phase == 'back':
                    if self.active:
                        if self.main.ready_in(self.name):
                            # log.info(f'Ack {self.name}')
                            self.active = False
                            intf.ack()
                        else:
                            pass
                            # log.info(f'NAck {self.name}')
                    await clk()

            except (BrokenPipeError, ConnectionResetError):
                intf.finish()
                raise GearDone

            # phase = await delta()


class OutCosimPort:
    def __init__(self, main, port, name=None):
        self.port = port
        self.name = name if name else port.basename
        self.done = False
        self.parent = None
        self.child = None
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
                # log.info(f'CosimPort {self.name} finished')
                intf.finish()
                raise GearDone

            try:
                # log.info(f'{self.name} read_out')
                data = self.main.read_out(self.name)
                # log.info(f'Put {data} -> {self.name}')
                await intf.put(data)
                # log.info(f'Ack {data} -> {self.name}')
                self.main.ack_out(self.name)
            except (BrokenPipeError, ConnectionResetError):
                intf.finish()
                raise GearDone
            except CosimNoData:
                pass

            await clk()
