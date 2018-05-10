class Port:
    def __init__(self,
                 node,
                 index,
                 basename,
                 producer=None,
                 consumer=None,
                 dtype=None):
        self.node = node
        self.index = index
        self.producer = producer
        self.consumer = consumer
        self.basename = basename
        self.dtype = dtype


class InPort(Port):
    pass


class OutPort(Port):
    pass
