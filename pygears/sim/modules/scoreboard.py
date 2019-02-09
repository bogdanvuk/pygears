from pygears import GearDone, gear
from pygears.sim import sim_assert, sim_log
from pygears.typing import Queue, typeof


def match_check(data, ref, tolerance):
    return (data >= (ref - tolerance)) and (data <= (ref + tolerance))


@gear
async def scoreboard(*din: b't', report, tolerance=0) -> None:
    cnt = 0
    match_cnt = 0
    try:
        while (1):
            items = []
            for d in din:
                items.append(await d.get())

            if tolerance != 0:
                if typeof(type(items[0]), Queue):
                    for v in items:
                        match = match_check(v.data, items[0].data, tolerance)
                        if match:
                            match = v.eot == items[0].eot

                        if not match:
                            break
                else:
                    for v in items:
                        match = match_check(v, items[0], tolerance)
                        if not match:
                            break
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
