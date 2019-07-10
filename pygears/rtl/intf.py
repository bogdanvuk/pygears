import functools

from pygears.core.hier_node import NamedHierNode
from pygears.rtl.port import InPort, OutPort


class RTLIntf(NamedHierNode):
    def __init__(self, parent, dtype, producer=None, consumers=[]):
        super().__init__(basename=None, parent=parent)
        self.consumers = consumers.copy()
        self.producer = producer
        if producer is not None:
            self.producer.consumer = self

        self.dtype = dtype

    @property
    @functools.lru_cache(maxsize=None)
    def _basename(self):
        producer_port = self.producer
        port_name = producer_port.basename

        if isinstance(producer_port, InPort):
            return port_name
        elif ((not self.is_broadcast) and self.consumers
              and isinstance(self.consumers[0], OutPort)):
            return self.consumers[0].basename
        elif hasattr(self, 'var_name'):
            return self.var_name
        elif self.sole_intf:
            return f'{producer_port.node.basename}'
        else:
            return f'{producer_port.node.basename}_{port_name}'

    @property
    @functools.lru_cache(maxsize=None)
    def basename(self):
        basename = self._basename
        if self.is_port_intf:
            return basename

        for c in self.parent.child:
            if c is not self and c._basename == basename:
                return f'{self._basename}_s'

        for p in self.parent.out_ports:
            if p.basename == basename:
                return f'{self._basename}_s'

        return basename


        # sibling_names = [
        #     c._basename for c in self.parent.child if c is not self
        # ]

        # port_names = [p.basename for p in self.parent.out_ports]

        # if not self.is_port_intf and (self._basename in (
        #         sibling_names + port_names)):
        #     return f'{self._basename}_s'
        # else:
        #     return self._basename

    @property
    def outname(self):
        if self.is_broadcast:
            return f'{self.basename}_bc'
        else:
            return self.basename

    # @property
    # def name(self):
    #     parent = self.parent
    #     hier = [self.basename]
    #     while parent:
    #         hier.append(parent.inst_basename)
    #         parent = parent.parent

    #     return '.'.join(reversed(hier))

    @property
    def sole_intf(self):
        if self.producer:
            return len(self.producer.node.out_ports) == 1
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
