from pygears.typing import Tuple, Uint, Int, Queue
from pygears.sim.modules.svrand import (create_type_cons,
                                        get_svrand_constraint, SVRandSocket)
import threading
import pprint

t_cfg = Tuple[{'x': Uint[3], 'y': Uint[2], 'z': Int[8]}]
t_din = Queue[Tuple[{'a': Uint[3], 'b': Uint[2]}]]
t_ain = Queue[Uint[16], 5]
outdir = '/tools/home/tmp1'

cons = []
cons.append(
    create_type_cons(
        t_cfg,
        'cfg',
        scale=Uint[4],
        cons=['scale > 0', 'cfg.z > cfg.x', '(cfg.x - cfg.y) == scale*cfg.y']))
cons.append(create_type_cons(t_din, 'din', cons=['din.eot == 0']))
cons.append(
    create_type_cons(t_ain, 'ain', cons=['ain.eot != 0', 'ain.data == 10']))

# pp = pprint.PrettyPrinter(indent=2)
# for c in cons:
#     pp.pprint(vars(c))


def start_cadence():
    get_svrand_constraint(outdir, cons)


def get_random_data():
    soc = SVRandSocket(cons)

    for i in range(1, 3):
        print(f'test_rand: Try to get data #{i}')
        data = soc.get_rand('cfg')
        print(f'test_rand: cfg got {data}')
        data = soc.get_rand('din')
        print(f'test_rand: din got {data}')
        data = soc.get_rand('ain')
        print(f'test_rand: ain got {data}')

    soc.finish()


if __name__ == '__main__':
    tasks = [get_random_data, start_cadence]

    for task in tasks:
        t = threading.Thread(target=task)
        t.start()
