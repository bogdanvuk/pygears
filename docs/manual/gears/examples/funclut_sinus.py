from math import pi, sin
from pygears.lib import funclut, drv, check
from pygears.typing import Fixp

drv(t=Fixp[3, 16], seq=[-pi/6, pi/6, pi/4, pi/2]) \
    | funclut(f=sin) \
    | check(ref=[sin(-pi/6), sin(pi/6), sin(pi/4), sin(pi/2)],
            cmp=lambda x, y: abs(x-y) <= 1)
