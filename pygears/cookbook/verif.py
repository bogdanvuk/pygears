from pygears import gear
from pygears.sim import drv, mon, scoreboard, sim_assert


@gear
async def check(din, *, ref):
    try:
        items = []
        while (1):
            items.append(await din.get())
    finally:
        print(f"Here: {items}")
        print(f"{ref}")
        print(f"{items == ref}")
        sim_assert(items == ref)


def tlm_verif(*seq, f, ref):
    res_tlm = tuple(s | drv for s in seq) \
        | f \
        | mon

    ref_tlm = seq | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report


def verif(*seq, f, ref):
    stim = tuple(s | drv for s in seq)

    res_tlm = stim | f

    ref_tlm = stim | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report


def directed(*seq, f, ref):
    tuple(s | drv for s in seq) \
        | f \
        | mon \
        | check(ref=ref)


def directed_on_the_fly(*seq, f, ref):
    stim = tuple(s | drv for s in seq)

    res_tlm = stim | f

    report = []
    scoreboard(res_tlm, ref, report=report)

    return report
