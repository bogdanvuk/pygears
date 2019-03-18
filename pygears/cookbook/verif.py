from pygears import GearDone, gear
from pygears.common import decoupler
from pygears.sim import sim_assert
from pygears.sim.modules import drv, mon, scoreboard


@gear
async def check(din, *, ref):
    """Checks equality of input data with expected.

    Args:
        ref: A list of expected values

    Returns:
        None

    If type ``din`` is a :class:`Queue` of certain level, then ``ref`` should
    generate nested iterables of the same level
    """
    iter_ref = iter(ref)
    try:
        items = []
        while True:
            data = await din.get()
            items.append(data)
            sim_assert(data == next(iter_ref),
                       f'mismatch. Got: {items}, expected: {ref}')
    except (GearDone, StopIteration):
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
    """Verification environment for comparing DUV results with reference model.
    The environment instantiates the DUV and reference model and drives the
    passed stimulus to both. The outpus are passed to the scoreboard which
    compares the results. Outputs are decoupled to ensure there is no connection
    between the DUV and the environment. Optional delays can be added to all
    input and output interfaces.

    Args:
        stim: Input stimulus
        f: Gear to be verified
        ref: Gear used as reference model
        delays: List of delays for all inputs and outputs
        tolerance: Tolerance window when performing equality checks

    Returns:
        A report dictionary with pass/fail statistics
    """

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
    """Similar to ``verif`` function, except ``ref`` is a list of expected results"""
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
    """Similar to ``directed`` function, except ``ref`` is a generator and
    checking is done `on-the-fly`"""
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
