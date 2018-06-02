import asyncio
import random

class Module:
    def __init__(self, in_ports, out_ports):
        pass

    def connect(self, port):
        if len(out_ports) == 1:
            self.out_ports[0].connect(port)

async def produce(queue, n):
    for x in range(n):
        # produce an item
        print('producing {}/{}'.format(x, n))
        # simulate i/o operation using sleep
        item = str(x)

        # put the item in the queue
        for q in queue:
            q.put_nowait(item)

        await asyncio.wait([q.join() for q in queue])

        print('all done')

        await asyncio.sleep(1)


async def consume(queue, cid):
    while True:
        # wait for an item from the producer
        item = await queue.get()

        # process the item
        print('{}: consuming {}...'.format(cid, item))
        # Notify the queue that the item has been processed
        queue.task_done()

        # simulate i/o operation using sleep
        await asyncio.sleep(2+cid)


async def run(n):
    queue = [asyncio.Queue(maxsize=1) for _ in range(2)]
    # schedule the consumer
    consumer = [
        asyncio.ensure_future(consume(q, i)) for i, q in enumerate(queue)
    ]

    # run the producer and wait for completion
    await produce(queue, n)
    # the consumer is still awaiting for an item, cancel it
    for c in consumer:
        c.cancel()


loop = asyncio.get_event_loop()
loop.run_until_complete(run(10))
loop.close()
