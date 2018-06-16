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

    tasks = {proc.run(): proc for proc in registry('SimMap').values()}

    bind('SimTasks', tasks)

    loop.run_until_complete(
        asyncio.gather(*tasks.keys()))
    loop.close()


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SimFlow'] = [sim_inst]
        cls.registry['SimTasks'] = {}
        cls.registry['SimConfig'] = {'dbg_assert': False}

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
