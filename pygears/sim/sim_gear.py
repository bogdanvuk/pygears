import inspect
import asyncio
from pygears.core.err import register_exit_hook
from pygears import registry, GearDone
from pygears.sim import clk, timestep, delta, sim_log, sim_phase
from pygears.typing_common.codec import code
from pygears.typing import typeof, TLM


def is_async_gen(func):
    return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)


def is_simgear_func(func):
    return inspect.iscoroutinefunction(func) or is_async_gen(func)


class SimGear:
    def __init__(self, gear):
        self.gear = gear
        self.out_queues = []
        self.namespace = registry('SimMap')
        self._done = False
        if not hasattr(self, 'func'):
            self.func = gear.func

    @property
    def sim_func_args(self):
        args = []
        for p in self.gear.in_ports:
            args.append(p.consumer)

        kwds = {
            k: self.gear.params[k]
            for k in self.gear.kwdnames if k in self.gear.params
        }

        return args, kwds

    def finish(self):
        # self._done
        # self.task.cancel()
        for port in self.gear.out_ports:
            port.producer.finish()

        self.cleanup()

    def cleanup(self):
        pass

    def setup(self):
        register_exit_hook(self.cleanup)
        if self.gear.params['sim_setup'] is not None:
            self.gear.params['sim_setup'](self.gear)

    async def run(self):
        self.task = asyncio.Task.current_task()
        args, kwds = self.sim_func_args
        try:
            while (1):
                if is_async_gen(self.func):
                    async for val in self.func(*args, **kwds):
                        if sim_phase() == 'back':
                            await clk()

                        if val is not None:
                            if len(self.gear.out_ports) == 1:
                                val = (val, )

                            for p, v in zip(self.gear.out_ports, val):
                                if v is not None:
                                    p.producer.put_nb(v)

                            for p, v in zip(self.gear.out_ports, val):
                                if v is not None:
                                    await p.producer.ready()

                else:
                    await self.func(*args, **kwds)

                if args:
                    if all(a.done() for a in args):
                        raise GearDone

        except GearDone as e:
            # print(f"SimGear canceling: {self.gear.name}")
            self.finish()
            raise e
