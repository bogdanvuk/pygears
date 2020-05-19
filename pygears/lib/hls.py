from pygears.conf import reg
from pygears.core.intf import IntfOperPlugin


async def qiter(intf):
    while True:
        data = await intf.pull()

        yield data

        intf.ack()

        if all(data.eot):
            break


class gather:
    def __init__(self, *din):
        self.din = din

    async def __aenter__(self):
        din_data = []
        for d in self.din:
            din_data.append(await d.pull())

        return tuple(din_data)

    async def __aexit__(self, exception_type, exception_value, traceback):
        for d in self.din:
            d.ack()


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        reg['gear/intf_oper/__aiter__'] = qiter
