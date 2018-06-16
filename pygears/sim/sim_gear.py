import asyncio
import inspect
from pygears import registry, GearDone


def is_async_gen(func):
    return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)


def is_simgear_func(func):
    return inspect.iscoroutinefunction(func) or is_async_gen(func)


class SimGear:
    def __init__(self, gear):
        self.gear = gear
        self.out_queues = []
        self.namespace = registry('SimMap')
        if not hasattr(self, 'func'):
            self.func = gear.func

        # for p in gear.out_ports:
        #     out_intf = p.consumer
        #     consumers = out_intf.consumers
        #     self.out_queues.append(
        #         [asyncio.Queue(maxsize=1) for _ in consumers])

    # def get_queue(self, port, consumer):
    #     out_intf = port.consumer
    #     cons_index = out_intf.consumers.index(consumer)
    #     return self.out_queues[port.index][cons_index]

    @property
    def sim_func_args(self):
        args = []
        for p in self.gear.in_ports:
            # prod_intf = p.producer
            # prod_port = prod_intf.producer
            # prod_sim = self.namespace[prod_port.gear]
            # args.append(prod_sim.get_queue(prod_port, p))
            args.append(p.consumer)

        kwds = {
            k: self.gear.params[k]
            for k in self.gear.kwdnames if k in self.gear.params
        }

        return args, kwds

    # async def output(self, val, dout_id):
    #     for q in self.out_queues[dout_id]:
    #         q.put_nowait(val)

    #     await asyncio.wait([q.join() for q in self.out_queues[dout_id]])

    async def run(self):
        args, kwds = self.sim_func_args

        try:
            while (1):
                if is_async_gen(self.func):
                    async for val in self.func(*args, **kwds):
                        if len(self.gear.out_ports) == 1:
                            val = (val, )

                        for p, v in zip(self.gear.out_ports,val):
                            if v is not None:
                                await p.producer.put(v)
                else:
                    await self.func(*args, **kwds)
        except GearDone:

            for port in self.gear.out_ports:
                port.producer.finish()
            for a in args:
                a.finish()

            print(f"SimGear canceling: {self.gear.name}")
