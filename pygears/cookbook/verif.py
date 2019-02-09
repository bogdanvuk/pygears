from pygears import gear, GearDone
from pygears.sim import sim_assert
from pygears.sim.modules import delay_mon, drv, mon, scoreboard
from pygears.sim.utils import SimDelay
from pygears.common import decoupler


@gear
async def check(din, *, ref):
    try:
        items = []
        while (1):
            items.append(await din.get())
    except GearDone:
        # print(f"Here: {items}")
        # print(f"{ref}")
        # print(f"{items == ref}")
        sim_assert(items == ref, f'mismatch. Got: {items}, expected: {ref}')


def tlm_verif(*seq, f, ref):
    res_tlm = tuple(s | drv for s in seq) \
        | f \
        | mon

    ref_tlm = seq | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report


def verif(*stim, f, ref, delays=None, tolerance=0):
    '''Using ref. model'''

    res_tlm = stim | f
    ref_tlm = stim | ref

    if not isinstance(res_tlm, tuple):
        res_tlm = (res_tlm, )
        ref_tlm = (ref_tlm, )

    report = [[] for _ in range(len(res_tlm))]

    if delays is None:
        delays = (None, ) * len(res_tlm)

    assert len(ref_tlm) == len(res_tlm)
    assert len(delays) == len(res_tlm)

    for r, res_intf, ref_intf, d in zip(report, res_tlm, ref_tlm, delays):
        if d is not None:
            res_intf = res_intf | d

        res_intf = res_intf | decoupler(depth=0)
        ref_intf = ref_intf | decoupler(depth=0)

        scoreboard(res_intf, ref_intf, report=r, tolerance=tolerance)

    return report


def directed(*stim, f, ref, delays=None):
    '''Directed test, ref is a list of expected results'''
    res = stim | f

    if not isinstance(res, tuple):
        res = (res, )
        ref = (ref, )

    if delays is None:
        delays = (None, ) * len(res)

    assert len(ref) == len(res)
    assert len(delays) == len(res)

    for ref_inst, res_inst, delay_inst in zip(ref, res, delays):
        if delay_inst is not None:
            res_inst = res_inst | delay_inst
        res_inst | mon | check(ref=ref_inst)


def directed_on_the_fly(*stim, f, refs, delays=None):
    '''Directed test, but checking done on-the-fly (from generators)'''
    res_tlm = stim | f

    if not isinstance(res_tlm, tuple):
        res_tlm = (res_tlm, )

    if delays is None:
        delays = (None, ) * len(res_tlm)

    report = [[] for _ in range(len(res_tlm))]
    for r, res_intf, ref, d in zip(report, res_tlm, refs, delays):
        if d is not None:
            res_intf = res_intf | d

        res_intf = res_intf | decoupler(depth=0)
        # ref = ref | decoupler(depth=0)

        scoreboard(res_intf, ref, report=r)

    return report
