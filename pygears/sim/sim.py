import asyncio

import tempfile

from pygears import registry, find, PluginBase, bind
from pygears.sim.inst import sim_inst
from concurrent.futures import CancelledError, TimeoutError
from pygears.sim import drv, mon, scoreboard


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
    # for t, sim_gear in zip(tasks, registry('SimMap').values()):
    #     t.gear = sim_gear.gear

    bind('SimTasks', tasks)

    finished, pending = loop.run_until_complete(
        asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED))

    # queue_joins = []
    # for proc in registry('SimMap').values():
    #     for out_q in proc.out_queues:
    #         for q in out_q:
    #             pending.append(q.join())

    # finished, pending = loop.run_until_complete(
    #     asyncio.wait(queue_joins))

    try:
        loop.run_until_complete(
            asyncio.wait_for(asyncio.gather(*pending), 0.5))
    except TimeoutError:  # Any other exception would be bad
        pass

    print("Simulation finished, canceling other tasks")
    # Cancel the remaining tasks
    for task in pending:
        task.cancel()

    # loop.run_until_complete(asyncio.gather(*pending))
    try:
        loop.run_until_complete(asyncio.gather(*pending))
    except CancelledError:  # Any other exception would be bad
        pass

    print("Tasks canceled, closing the loop")
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
