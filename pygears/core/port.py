class Port:
    def __init__(self, gear, index, basename, producer=None, consumer=None):
        self.gear = gear
        self.index = index
        self.producer = producer
        self.consumer = consumer
        self.basename = basename

    @property
    def name(self):
        return f'{self.gear.name}.{self.basename}'

    @property
    def dtype(self):
        if self.producer is not None:
            return self.producer.dtype
        else:
            return self.consumer.dtype

    def finish(self):
        self.consumer.finish()


class InPort(Port):
    direction = "in"

    @property
    def dtype(self):
        if self.consumer is not None:
            return self.consumer.dtype
        else:
            return self.producer.dtype


class OutPort(Port):
    direction = "out"
