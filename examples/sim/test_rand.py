from pygears.typing import Tuple, Uint, Int, Queue
from pygears.sim.modules.svrand import create_type_cons, get_svrand_constraint

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

pp = pprint.PrettyPrinter(indent=2)
for c in cons:
    pp.pprint(vars(c))

get_svrand_constraint(outdir, cons)
