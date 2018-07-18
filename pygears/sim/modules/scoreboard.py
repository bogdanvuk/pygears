from pygears import gear, GearDone, module
from pygears.sim import sim_assert


@gear
async def scoreboard(*din: b't', report) -> None:
    cnt = 0
    match_cnt = 0
    try:
        while (1):
            items = []
            for d in din:
                items.append(await d.get())

            match = all(v == items[0] for v in items)

            report.append({'match': match, 'items': items})
            cnt += 1
            if match:
                match_cnt += 1
            sim_assert(
                match,
                f'{module().name}: mismatch on #{cnt}: {items[0]}, {items[1]}')

    except GearDone as e:
        print(f'{module().name}: Number of matches = {match_cnt}/{cnt}')
        raise e
