class Port:
    def __init__(self, svmod, gear_port):
        self.svmod = svmod
        self.index = gear_port.index
        self.producer = gear_port.producer
        self.consumer = gear_port.consumer
        self.basename = gear_port.basename
        self.dtype = gear_port.dtype


class InPort(Port):
    pass


class OutPort(Port):
    pass
