import asyncio

import tempfile

from pygears import registry, find, PluginBase, bind
from pygears.sim.inst import sim_inst
from concurrent.futures import CancelledError
from pygears.sim import drv, mon, scoreboard


def cur_gear():
    cur_task = asyncio.Task.current_task()
    sim_gear = registry('SimTasks')[cur_task._coro]
    return sim_gear.gear


def artifacts_dir():
    return registry('SimArtifactDir')


def sim(**conf):
    if "outdir" not in conf:
        conf["outdir"] = tempfile.mkdtemp()

    bind('SimArtifactDir', conf['outdir'])

    top = find('/')
    for oper in registry('SimFlow'):
        top = oper(top, conf)

    loop = asyncio.new_event_loop()

    tasks = {proc.run(): proc for proc in registry('SimMap').values()}
    # for t, sim_gear in zip(tasks, registry('SimMap').values()):
    #     t.gear = sim_gear.gear

    bind('SimTasks', tasks)

    finished, pending = loop.run_until_complete(
        asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED))

    # Cancel the remaining tasks
    for task in pending:
        task.cancel()

    try:
        loop.run_until_complete(asyncio.gather(*pending))
    except CancelledError:  # Any other exception would be bad
        pass

    loop.close()


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SimFlow'] = [sim_inst]
        cls.registry['SimTasks'] = {}

    @classmethod
    def reset(cls):
        bind('SimTasks', {})


def verif(*seq, f, ref):
    res_tlm = tuple(s | drv for s in seq) \
        | f \
        | mon

    ref_tlm = seq | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report
