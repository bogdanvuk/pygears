from pygears import gear
from pygears.typing import Integer, Tuple, Uint

TData = Integer['xlen']
TReadRequest = Uint[5]
TWriteRequest = Tuple[{'addr': Uint[5], 'data': TData}]


@gear
async def register_file_write(request: TWriteRequest, *, reg_mem):
    async with request as req:
        reg_mem[req['addr']] = req['data']


@gear
async def register_file_read(request: TReadRequest, *, reg_mem) -> TData:
    async with request as req:
        yield reg_mem[req]


@gear
def register_file(read_request: TReadRequest, write_request: TWriteRequest, *,
                  reg_mem) -> TData:

    write_request | register_file_write(reg_mem=reg_mem)
    return read_request | register_file_read(reg_mem=reg_mem)
