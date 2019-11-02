from math import pi, sin
from pygears.lib import funclut, drv, scope
from pygears.typing import Fixp

drv(t=Fixp[3, 16], seq=[2 * pi / 100 * x - pi for x in range(101)]) \
    | funclut(f=sin) \
    | scope(title='sine')
