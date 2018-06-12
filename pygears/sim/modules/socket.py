import socket
import asyncio
import array
from math import ceil

from pygears.sim.sim_gear import SimGear
from pygears.sim.modules.drv import TypeDrvVisitor
from pygears.typing import Uint

def u32_repr_gen(data, dtype):
    yield int(dtype)
    for i in range(ceil(int(dtype) / 32)):
        yield data & 0xffffffff
        data >>= 32

def u32_repr(data, dtype):
    return array.array('I', u32_repr_gen(data, dtype))

class SimSocket(SimGear):
    def __init__(self, gear):
        super().__init__(gear)

        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ('localhost', 1234)
        print('starting up on %s port %s' % server_address)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)

        self.sock.bind(server_address)

        # Listen for incoming connections
        self.sock.listen(5)

    async def handler(self, conn, din, dtype):
        while True:
            item = await din.get()
            din.task_done()

            pkt = u32_repr(item, dtype).tobytes()

            # print("Handler thread started")
            # msg = await self.loop.sock_recv(conn, 1024)
            # print(f"Received: {msg}")
            # if not msg:
            #     break
            await self.loop.sock_sendall(conn, pkt)
        conn.close()

    async def func(self, *args, **kwds):
        self.loop = asyncio.get_event_loop()

        print(self.gear.argnames)

        while True:
            print("Wait for connection")
            conn, addr = await self.loop.sock_accept(self.sock)

            print("Connection received")
            msg = await self.loop.sock_recv(conn, 1024)
            port_name = msg.decode()
            try:
                i = self.gear.argnames.index(msg.decode())
                self.loop.create_task(
                    self.handler(conn, args[i], self.gear.in_ports[i].dtype))
            except ValueError:
                print(f"Nonexistant port {port_name}")
                conn.close()
