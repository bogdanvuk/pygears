from pygears import gear, registry, find, config
from pygears.lib import const
from pygears.typing import Uint, Int
from pygears.lib import directed, drv, add
from pygears.sim import sim, cosim
from pygears.core.hier_node import HierYielderBase


# def test_simple_out_only():
#     config['gear/memoize'] = True
#     directed(drv(t=Uint[4], seq=[7]), drv(t=Uint[4], seq=[7]), f=add, ref=[14])
#     sim()


class MemoizedVisitor(HierYielderBase):
    def Gear(self, node):
        if 'memoized' in node.params:
            yield node


def check_memoized(*paths):
    mem_paths = set(g.name for g in MemoizedVisitor().visit(find('/')))

    return all(p in mem_paths for p in paths)


def test_hier_level1():
    config['gear/memoize'] = True

    @gear
    def test(a, b):
        return a + b

    @gear
    def top(a, b, c, d):
        t0 = test(a, b)
        t1 = test(c, d)
        return t0 + t1

    directed(drv(t=Uint[4], seq=[1]),
             drv(t=Uint[4], seq=[2]),
             drv(t=Uint[4], seq=[3]),
             drv(t=Uint[4], seq=[4]),
             f=top,
             ref=[10])

    assert check_memoized('/top/test1')

    sim()

def test_hier_level2():
    config['gear/memoize'] = True
    @gear
    def test(a, b):
        return a + b

    @gear
    def test_hier(a, b, c, d):
        return test(a, b) + test(c, d)

    @gear
    def top(a, b, c, d):
        return test_hier(a, b, c, d) + test_hier(a, b, c, d)

    directed(drv(t=Uint[4], seq=[1]),
             drv(t=Uint[4], seq=[2]),
             drv(t=Uint[4], seq=[3]),
             drv(t=Uint[4], seq=[4]),
             f=top,
             ref=[20])

    assert check_memoized('/top/test_hier1', '/top/test_hier0/test1')

    cosim('/top', 'verilator')

    sim()
