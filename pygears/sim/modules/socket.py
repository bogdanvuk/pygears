import socket
import asyncio
import array
from math import ceil

from pygears.sim.sim_gear import SimGear


def u32_repr_gen(data, dtype):
    yield int(dtype)
    for i in range(ceil(int(dtype) / 32)):
        yield data & 0xffffffff
        data >>= 32


def u32_repr(data, dtype):
    return array.array('I', u32_repr_gen(data, dtype))

def u32_bytes_to_int(data):
    arr = array.array('I')
    arr.frombytes(data)
    val = 0
    for val32 in reversed(arr):
        val <<= 32
        val |= val32

    return val


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
        self.handlers = []

    async def out_handler(self, conn, din, dtype):
        while True:
            try:
                item = await din.get()
            except asyncio.CancelledError as e:
                await self.loop.sock_sendall(conn, b'\x00')
                conn.close()
                raise e

            pkt = u32_repr(item, dtype).tobytes()
            await self.loop.sock_sendall(conn, pkt)

            try:
                await self.loop.sock_recv(conn, 1024)
            except asyncio.CancelledError as e:
                conn.close()
                raise e

            din.task_done()

    async def in_handler(self, conn, dout_id, dtype):
        try:
            while True:
                print("Wait for input data")
                item = await self.loop.sock_recv(conn, 1024)

                print(f"Output data {item}, of len {len(item)}")

                await self.output(u32_bytes_to_int(item), dout_id)

        except asyncio.CancelledError as e:
            conn.close()
            raise e
        except Exception as e:
            print(f"Exception in socket handler: {e}")


    def make_out_handler(self, name, conn, args):
        try:
            i = self.gear.argnames.index(name)
            return self.loop.create_task(
                self.out_handler(conn, args[i], self.gear.in_ports[i].dtype))

        except ValueError:
            pass

    def make_in_handler(self, name, conn, args):
        try:
            print(self.gear.outnames)
            print(name)
            i = self.gear.outnames.index(name)
            print(i)
            return self.loop.create_task(
                self.in_handler(conn, i, self.gear.out_ports[i].dtype))

        except ValueError:
            pass

    async def func(self, *args, **kwds):
        self.loop = asyncio.get_event_loop()

        print(self.gear.argnames)

        try:
            while True:
                print("Wait for connection")
                conn, addr = await self.loop.sock_accept(self.sock)

                msg = await self.loop.sock_recv(conn, 1024)
                port_name = msg.decode()

                print(f"Connection received for {port_name}")

                handler = self.make_out_handler(port_name, conn, args)
                if handler is None:
                    print("Trying in port")
                    handler = self.make_in_handler(port_name, conn, args)

                if handler is None:
                    print(f"Nonexistant port {port_name}")
                    conn.close()
                else:
                    self.handlers.append(handler)

        except asyncio.CancelledError as e:
            for h in self.handlers:
                h.cancel()

            raise e
