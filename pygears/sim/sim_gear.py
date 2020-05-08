import sys
import inspect
import atexit
from pygears.conf.trace import register_exit_hook, TraceException, make_traceback
from pygears import reg, GearDone
from pygears.core.channel import report_out_dangling
from pygears.sim import clk, timestep
from pygears.sim.sim import schedule_to_finish
from pygears.conf.trace import gear_definition_location


def is_async_gen(func):
    return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)


def is_simgear_func(func):
    return (
        inspect.isgeneratorfunction(func) or inspect.iscoroutinefunction(func)
        or is_async_gen(func))


class SimulationError(TraceException):
    pass


class SimGear:
    def __init__(self, gear):
        self.gear = gear
        self.done = False
        self._clean = True
        if not hasattr(self, 'func'):
            self.func = gear.func

        for p in gear.out_ports:
            if p.consumer.consumers:
                continue

            report_out_dangling(p)

    def setup(self):
        self._clean = False
        atexit.register(self._finish)
        register_exit_hook(self._cleanup)
        if self.gear.params['sim_setup'] is not None:
            self.gear.params['sim_setup'](self.gear)

    async def run(self):
        args, kwds = self.sim_func_args

        out_prods = [p.producer for p in self.gear.out_ports]
        single_output = len(out_prods) == 1
        if single_output:
            out_prods = out_prods[0]

        sim = reg['sim/simulator']
        err = None

        try:
            if is_async_gen(self.func):
                while (1):
                    if sim.phase != 'forward':
                        await clk()

                    async_gen = self.func(*args, **kwds)

                    async for val in async_gen:
                        if sim.phase != 'forward':
                            await clk()

                        if val is not None:
                            if single_output:
                                tb = None
                                try:
                                    out_prods.put_nb(val)
                                except GearDone:
                                    raise
                                except Exception as e:
                                    func, fn, ln = gear_definition_location(self.func)

                                    err = SimulationError(
                                        f"inside '{self.gear.name}': {repr(e)}",
                                        async_gen.ag_frame.f_lineno,
                                        filename=fn)

                                    traceback = make_traceback((SimulationError, err, sys.exc_info()[2]))
                                    exc_type, exc_value, tb = traceback.standard_exc_info

                                if tb is not None:
                                    raise exc_value.with_traceback(tb)

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
            elif inspect.isgeneratorfunction(self.func):
                while (1):
                    if sim.phase != 'forward':
                        await clk()

                    for val in self.func(*args, **kwds):
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
                    # TODO: handle case where self.func is empty and this loop
                    # will just go on forever freezing everything. It happens
                    # if the user accidently creates empty "async def" function
                    await self.func(*args, **kwds)

                    if args:
                        if all(a.done for a in args):
                            raise GearDone

        except GearDone as e:
            for p in self.gear.in_ports:
                intf = p.consumer
                try:
                    if not intf.empty():
                        prod_intf = intf.in_queue.intf
                        prod_gear = prod_intf.consumers[0].gear
                        schedule_to_finish(prod_gear)
                except GearDone:
                    pass

            self._finish()
            raise e
        except Exception as e:
            e.args = (f'{str(e)}, in the module "{self.gear.name}"', )
            err = e

        if err:
            raise err

    @property
    def sim_func_args(self):
        args = []
        for p in self.gear.in_ports:
            args.append(p.consumer)

        return args, self.gear.explicit_params

    def _finish(self):
        self.done = True
        for port in self.gear.out_ports:
            port.producer.finish()

        if not self._clean:
            self._cleanup()

    def _cleanup(self):
        self._clean = True
