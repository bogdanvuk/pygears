import inspect
import asyncio
import atexit
from pygears.conf.trace import register_exit_hook
from pygears import registry, GearDone
from pygears.sim import clk
from pygears.sim.sim import schedule_to_finish


def is_async_gen(func):
    return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)


def is_simgear_func(func):
    return inspect.iscoroutinefunction(func) or is_async_gen(func)


class SimGear:
    def __init__(self, gear):
        self.gear = gear
        self.done = False
        self._clean = True
        if not hasattr(self, 'func'):
            self.func = gear.func

    def setup(self):
        self._clean = False
        atexit.register(self._finish)
        register_exit_hook(self._cleanup)
        if self.gear.params['sim_setup'] is not None:
            self.gear.params['sim_setup'](self.gear)

    async def run(self):
        self.task = asyncio.Task.current_task()
        args, kwds = self.sim_func_args

        out_prods = [p.producer for p in self.gear.out_ports]
        single_output = len(out_prods) == 1
        if single_output:
            out_prods = out_prods[0]

        sim = registry('sim/simulator')

        try:
            if is_async_gen(self.func):
                while (1):
                    if sim.phase != 'forward':
                        await clk()

                    async for val in self.func(*args, **kwds):
                        if sim.phase != 'forward':
                            await clk()

                        if val is not None:
                            if single_output:
                                out_prods.put_nb(val)
                                await out_prods.ready()
                            else:
                                for p, v in zip(out_prods, val):
                                    if v is not None:
                                        p.put_nb(v)

                                for p, v in zip(out_prods, val):
                                    if v is not None:
                                        await p.ready()

                    if args:
                        if all(a.done for a in args):
                            raise GearDone
            else:
                while (1):
                    await self.func(*args, **kwds)

                    if args:
                        if all(a.done for a in args):
                            raise GearDone

        except GearDone as e:
            for p in self.gear.in_ports:
                intf = p.consumer
                if not intf.empty():
                    prod_intf = intf.in_queue.intf
                    prod_gear = prod_intf.consumers[0].gear
                    schedule_to_finish(prod_gear)

            self._finish()
            raise e

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

    def _finish(self):
        self.done = True
        for port in self.gear.out_ports:
            port.producer.finish()

        if not self._clean:
            self._cleanup()

    def _cleanup(self):
        self._clean = True
