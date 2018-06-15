from pygears.sim import drv, mon, scoreboard


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

