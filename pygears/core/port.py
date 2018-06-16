class Port:
    def __init__(self, gear, index, basename, producer=None, consumer=None):
        self.gear = gear
        self.index = index
        self.producer = producer
        self.consumer = consumer
        self.basename = basename

    @property
    def dtype(self):
        if self.producer is not None:
            return self.producer.dtype
        else:
            return self.consumer.dtype

    @property
    def queue(self):
        return self.producer.get_consumer_queue(self)

    def finish(self):
        self.consumer.finish()


class InPort(Port):
    pass


class OutPort(Port):
    pass
