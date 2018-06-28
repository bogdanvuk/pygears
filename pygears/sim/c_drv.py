import ctypes
from math import ceil
from pygears.typing_common.codec import code, decode


class IdleIteration(Exception):
    pass


class CGet:
    def __init__(self, verilib, name, dtype):
        self.c_get_api = getattr(verilib, f'get_{name}', None)

        self.dtype = dtype
        self.width = int(dtype)

        if self.width > 64:
            self.c_dtype = ctypes.c_uint * (ceil(self.width / 32))
        elif self.width > 32:
            self.c_dtype = ctypes.c_ulonglong
        else:
            self.c_dtype = ctypes.c_uint

    def from_c_data(self, data):
        dout = 0
        for d in reversed(list(data)):
            dout <<= 32
            dout |= d

        return dout

    def get(self):
        self.c_get_api(self.dout)
        return self.from_c_data(self.dout)


class CDrv:
    def __init__(self, verilib, port):
        self.verilib = verilib
        self.port = port

        self.data_posted = False
        self.done = False
        self.width = int(self.port.dtype)
        self.c_set_api = getattr(verilib, f'set_{port.basename}', None)
        self.c_get_api = getattr(verilib, f'get_{port.basename}', None)

        if self.width > 64:
            self.c_dtype = ctypes.c_uint * (ceil(self.width / 32))
        elif self.width > 32:
            self.c_dtype = ctypes.c_ulonglong
        else:
            self.c_dtype = ctypes.c_uint


class CInputDrv(CDrv):
    def __init__(self, verilib, seq, port):
        super().__init__(verilib, port)
        self.c_set_api.argtypes = (self.c_dtype, ctypes.c_uint)
        self.seq = seq

    def to_c_data(self, data):
        if self.width > 64:

            def dgen(data):
                for i in range(ceil(self.width / 32)):
                    yield data & 0xffffffff
                    data >>= 32

            return self.c_dtype(*list(dgen(data)))
        else:
            return self.c_dtype(data)

    def empty(self):
        return self.seq.empty()

    async def post(self):
        if self.data_posted:
            return

        data = await self.seq.pull()
        print("Data received: ", data)

        self.data_posted = True
        self.acked = False
        self.c_set_api(self.to_c_data(code(self.port.dtype, data)), 1)

    def ack(self):
        if self.data_posted:
            self.acked = self.c_get_api()
            if self.acked:
                self.seq.ack()

    def cycle(self):
        if self.acked:
            self.data_posted = False
            self.c_set_api(self.to_c_data(0), 0)


class COutputDrv(CDrv):
    def __init__(self, verilib, port):
        super().__init__(verilib, port)
        if self.width <= 64:
            self.c_dtype = self.c_dtype * 1
            self.c_get_api.argtypes = (self.c_dtype, )

        self.active = False
        self.dout = self.c_dtype()

    def from_c_data(self, data):
        dout = 0
        for d in reversed(list(data)):
            dout <<= 32
            dout |= d

        return dout

    def cycle(self):
        self.c_set_api(0)

    def ack(self):
        if self.active:
            self.active = False
            self.c_set_api(1)

    def read(self):
        self.active = self.c_get_api(self.dout)
        print(
            f'{self.port.basename}: {self.active}, {self.from_c_data(self.dout)}'
        )
        if self.active:
            return decode(self.port.dtype, self.from_c_data(self.dout))
        else:
            return None
