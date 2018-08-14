from pygears import gear, alternative, module
from pygears.typing import Array, Tuple, Uint, Queue
from pygears.util.utils import quiter_async, quiter


@gear
async def serialize(din: Array) -> b'din.dtype':
    async with din as val:
        for i in range(len(val)):
            yield val[i]


@alternative(serialize)
@gear
async def serialize_keep(
        din: Queue[Tuple[Array['dtype', 'width'], Uint['width']]]
) -> Queue['dtype']:

    async with din as qdata:
        data, active = qdata[0]

        active_out = [data[i] for i in range(len(data)) if active[i]]

        for d, last in quiter(active_out):
            yield module().tout((d, last and qdata.last))
