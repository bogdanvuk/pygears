from pygears import GearDone, gear
from pygears.sim import sim_assert, sim_log
from pygears.typing import Queue, typeof


def match_check(data, ref, tolerance):
    low = ref - tolerance
    high = ref + tolerance
    return low <= data <= high


def tolerance_check(items, tolerance):
    if typeof(type(items[0]), Queue):
        for val in items:
            match = match_check(val.data, items[0].data, tolerance)
            if match:
                match = val.eot == items[0].eot

            if not match:
                break
    else:
        for val in items:
            match = match_check(val, items[0], tolerance)
            if not match:
                break


@gear
async def scoreboard(*din: b't', report, tolerance=0) -> None:
    """Generic scoreboard used from comparing actual results from the DUT to
    expected results. Eventual mismatches are asserted using the ``sim_assert``
    function meaning that any ``error`` behaviour is controled via the ``sim``
    logger ``error`` settings.

    Args:
        din: Outputs from both the DUT and ref. model. All intpus are a PyGears
          interface
        report: List to with comparison results are appended
        tolerance: Optional tolerance when comparing results. The DUT result must
          be in the (expected - tolerance, expected+tolerance) range

    Returns:
        None
    """
    cnt = 0
    match_cnt = 0
    try:
        while True:
            items = []
            for d in din:
                items.append(await d.get())

            if tolerance != 0:
                tolerance_check(items, tolerance)
            else:
                match = all(v == items[0] for v in items)

            report.append({'match': match, 'items': items})
            cnt += 1
            if match:
                match_cnt += 1
            sim_assert(match, f'mismatch on #{cnt}: {items[0]}, {items[1]}')

    except GearDone as e:
        sim_log().info(f'Number of matches = {match_cnt}/{cnt}')
        raise e
