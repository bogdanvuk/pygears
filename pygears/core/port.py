import weakref

from functools import partial


# def callback(p, b):
#     print(f'Consumer of {p.name} consumer is deleted.')


class Port:
    def __init__(self, gear, index, basename, dtype=None, producer=None, consumer=None):
        self.gear = gear
        self.index = index
        self.producer = producer
        self._dtype = dtype
        # self._consumer = None if consumer is None else weakref.ref(consumer, partial(callback, self))
        self._consumer = None if consumer is None else weakref.ref(consumer)
        self.basename = basename

    @property
    def consumer(self):
        return self._consumer if self._consumer is None else self._consumer()

    @consumer.setter
    def consumer(self, val):
        # self._consumer = weakref.ref(val, partial(callback, self))
        self._consumer = weakref.ref(val)

    @property
    def name(self):
        return f'{self.gear.name}.{self.basename}'

    @property
    def dtype(self):
        if self._dtype is not None:
            return self._dtype

        # TODO: Remove this later
        if self.producer is not None:
            return self.producer.dtype
        else:
            return self.consumer.dtype

    def finish(self):
        if self.consumer:
            self.consumer.finish()


class InPort(Port):
    direction = "in"

    @property
    def dtype(self):
        if self._dtype is not None:
            return self._dtype

        if self.consumer is not None:
            return self.consumer.dtype
        else:
            return self.producer.dtype

    def __repr__(self):
        return f'InPort("{self.name}")'


class OutPort(Port):
    direction = "out"

    def __repr__(self):
        return f'OutPort("{self.name}")'


class HDLUser:
    pass


class HDLProducer(HDLUser):
    pass


class HDLConsumer(HDLUser):
    pass
