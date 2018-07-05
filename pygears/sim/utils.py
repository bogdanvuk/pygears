import random


class SimDelay:
    def __init__(self, low, high):
        self.low = low
        self.high = high

    @property
    def delay(self):
        return random.randint(self.low, self.high)
