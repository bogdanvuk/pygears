from pygears.core.hier_node import NamedHierNode
from pygears.rtl.port import InPort, OutPort


class RTLIntf(NamedHierNode):
    def __init__(self, parent, dtype, producer=None, consumers=[]):
        super().__init__(basename=None, parent=parent)
        self.consumers = consumers.copy()
        self.producer = producer
        self.dtype = dtype

    @property
    def sole_intf(self):
        if self.producer:
            return len(self.producer.svmod.out_ports) == 1
        else:
            return True

    @property
    def is_broadcast(self):
        return len(self.consumers) > 1

    @property
    def is_port_intf(self):
        if isinstance(self.producer, InPort):
            return True
        elif ((not self.is_broadcast) and self.consumers
              and isinstance(self.consumers[0], OutPort)):
            return True
        else:
            return False

    def disconnect(self, port):
        if port in self.consumers:
            self.consumers.remove(port)
            port.producer = None
        elif port == self.producer:
            port.consumer = None
            self.producer = None

    def connect(self, port):
        self.consumers.append(port)
        port.producer = self
