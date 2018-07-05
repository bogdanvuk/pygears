import random

from pygears.sim import clk


class SimDelay:
    def __init__(self, low, high):
        self.low = low
        self.high = high

    @property
    async def delay(self):
        for i in range(random.randint(self.low, self.high)):
            await clk()
