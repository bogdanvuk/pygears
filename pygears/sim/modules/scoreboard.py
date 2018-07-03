from pygears import gear
from pygears.sim import sim_assert


@gear
async def scoreboard(*din: b't', report) -> None:
    cnt = 0
    while (1):
        items = []
        for d in din:
            items.append(await d.get())

        match = all(v == items[0] for v in items)

        report.append({'match': match, 'items': items})
        cnt += 1
        sim_assert(match, f'Scbd mismatch on #{cnt}: {items[0]}, {items[1]}')
