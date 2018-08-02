from pygears import gear
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
    finally:
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


def verif(*stim, f, ref, delays=None):
    '''Using ref. model'''
    # if delays is None:
    #     delays = [SimDelay(0, 0)] * (len(seq) + 1)
    # else:
    #     assert len(seq) + 1 == len(delays), print(
    #         'Not enough delays specified')

    # stim = tuple(s | drv(delay=delays[i]) for i, s in enumerate(seq))

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

        scoreboard(res_intf, ref_intf, report=r)

    return report


def directed(*stim, f, ref):
    '''Directed test, ref is a list of expected results'''
    res = stim | f
    if isinstance(res, tuple):
        for i, r in enumerate(res):
            r | mon | check(ref=ref[i])
    else:
        res | mon | check(ref=ref)


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
