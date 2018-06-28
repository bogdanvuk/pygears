from pygears import gear
from pygears.sim import sim_assert
import time


@gear
async def scoreboard(*din: b't', report) -> None:
    cnt = 0
    while (1):
        items = []
        for d in din:
            items.append(await d.get())

        match = all(v == items[0] for v in items)

        report.append({'match': match, 'items': items})
        print(f"#{cnt} scoreboard received: {items[0]}, {items[1]}")
        print(time.strftime('%X'))

        cnt += 1

        sim_assert(match)
