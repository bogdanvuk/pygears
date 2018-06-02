from pygears import gear
from pygears.typing import TLM


@gear
async def scoreboard(*din: TLM['t'], report, t=b't') -> None:
    while (1):
        items = []
        for d in din:
            items.append(await d.get())

        match = all(v == items[0] for v in items)

        report.append({'match': match, 'items': items})

        for d in din:
            d.task_done()
