import asyncio

import tempfile

from pygears import registry, find, PluginBase, bind
from pygears.sim.inst import sim_inst


def cur_gear():
    cur_task = asyncio.Task.current_task()
    sim_gear = registry('SimTasks')[cur_task._coro]
    return sim_gear.gear


def artifacts_dir():
    return registry('SimArtifactDir')


def custom_exception_handler(loop, context):
    # first, handle with default handler
    loop.default_exception_handler(context)

    exception = context.get('exception')
    if isinstance(exception, ZeroDivisionError):
        print(context)
        loop.stop()


async def idle():
    loop = asyncio.get_event_loop()
    clk = registry('ClkEvent')
    delta = registry('DeltaEvent')
    timestep = 0
    long_delayed = False

    while loop._ready:
        long_delayed = False
        while loop._ready:
            await asyncio.sleep(0)
            if not loop._ready:
                long_delayed = False
                delta.set()
                delta.clear()

            if (not loop._ready) and (not long_delayed):
                await asyncio.sleep(0)
                long_delayed = True

        print(f"-------------- {timestep} ------------------")
        timestep += 1
        bind('Timestep', timestep)
        clk.set()
        clk.clear()

    print("Loop empty: simulation done")


def timestep():
    return registry('Timestep')


def clk():
    return registry('ClkEvent').wait()


def delta():
    return registry('DeltaEvent').wait()


def sim(**conf):
    if "outdir" not in conf:
        conf["outdir"] = tempfile.mkdtemp()

    bind('SimArtifactDir', conf['outdir'])

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(custom_exception_handler)
    print("Creating a new loop: ", id(loop))

    top = find('/')
    for oper in registry('SimFlow'):
        top = oper(top, conf)

    setup_tasks = {proc.setup(): proc for proc in registry('SimMap').values()}
    tasks = {proc.run(): proc for proc in registry('SimMap').values()}

    bind('SimTasks', tasks)

    bind('ClkEvent', asyncio.Event())
    bind('DeltaEvent', asyncio.Event())
    bind('Timestep', 0)
    loop.run_until_complete(asyncio.gather(*setup_tasks.keys()))
    loop.run_until_complete(asyncio.gather(*tasks.keys(), idle()))
    loop.close()


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SimFlow'] = [sim_inst]
        cls.registry['SimTasks'] = {}
        cls.registry['SimConfig'] = {'dbg_assert': False}
        cls.registry['SVGenSystemVerilogImportPaths'] = []

    @classmethod
    def reset(cls):
        bind('SimTasks', {})


def sim_assert(cond, msg=None):
    if not cond:
        print(f'Assertion failed: {msg}')
        if registry('SimConfig')['dbg_assert']:
            import pdb
            pdb.set_trace()
        else:
            assert cond
