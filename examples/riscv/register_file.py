from pygears import gear
from pygears.sim import sim_log
from pygears.typing import Tuple, Uint

TAddr = Uint['w_addr']
TData = Uint['xlen']
TReadRequest = TAddr
TWriteRequest = Tuple[{'addr': TAddr, 'data': TData}]


@gear
async def register_file_write(request: TWriteRequest, *, storage):
    async with request as req:
        if req['addr'] != 0:
            sim_log().info(f'Writting {req["data"]} to {int(req["addr"])}')
            storage[int(req['addr'])] = req['data']


@gear
async def register_file_read(request: TReadRequest, *, storage,
                             t_dout) -> b't_dout':
    async with request as req:
        if req == 0:
            yield t_dout(0)
        else:
            yield storage[int(req)]


@gear
def register_file(read_request: TReadRequest,
                  write_request: TWriteRequest,
                  *,
                  storage,
                  xlen=b'xlen') -> TData:

    write_request | register_file_write(storage=storage)
    return read_request | register_file_read(
        storage=storage, t_dout=TData[xlen])
