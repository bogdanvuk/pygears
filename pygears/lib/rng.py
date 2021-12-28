from pygears import alternative, gear, module
from .ccat import ccat
from .cart import cart
from .fmap import fmap
from .permute import permuted_apply
from pygears.typing import Int, Integer, Queue, Tuple, typeof, code, Uint, Bool, cast
from pygears.util.utils import quiter
from .fmaps import queuemap
from .mux import mux

TCfg = Tuple[{
    'start': Integer['w_start'],
    'cnt': Integer['w_cnt'],
    'incr': Integer['w_incr']
}]


@gear
def qenumerate(*din: b'din_t'
               ) -> Queue[Tuple['din_t', Uint['bitw(len(din)-1)']]]:
    @gear
    def mux_wrap(sel):
        return mux(sel, *din) | Tuple

    return qrange(len(din)) | queuemap(f=mux_wrap)


def rng_out_type(cfg, cnt_steps):
    if cnt_steps:
        return cfg[0] + cfg[1] + cfg[2]

    return max(cfg[0], cfg[1])


def qrange_out_type(cfg):
    if typeof(cfg, Tuple):
        base = Int if any(c.signed for c in cfg) else Uint

        return cast(max(cfg[0], cfg[1]), base)

    return cfg


@gear(enablement=b'inclusive==False')
async def qrange(
        cfg: Tuple[{
            'start': Integer,
            'stop': Integer,
            'step': Integer
        }],
        *,
        inclusive=False,
) -> Queue['qrange_out_type(cfg)']:

    cnt: module().tout.data
    cur_cnt: cfg.dtype[0]
    last: Bool

    async with cfg as c:
        cnt = module().tout.data(c[0])
        last = False
        while not last:
            cur_cnt = cnt
            cnt += c[2]

            last = cnt >= c[1]
            yield cur_cnt, last


@alternative(qrange)
@gear(enablement=b'inclusive==False')
async def qrange_start_stop(
        cfg: Tuple[{
            'start': Integer,
            'stop': Integer
        }],
        *,
        inclusive=False,
) -> Queue['qrange_out_type(cfg)']:

    cnt: module().tout.data
    cur_cnt: cfg.dtype[0]
    last: Bool

    async with cfg as c:
        cnt = module().tout.data(c[0])
        last = False
        while not last:
            cur_cnt = cnt
            cnt += 1

            last = cnt == c[1]
            yield cur_cnt, cnt == c[1]


@alternative(qrange)
@gear(enablement=b'inclusive==True')
async def qrange_start_stop_inclusive(
        cfg: Tuple[{
            'start': Integer,
            'stop': Integer
        }],
        *,
        inclusive,
) -> Queue['qrange_out_type(cfg)']:
    cnt: module().tout.data
    last: Bool

    async with cfg as c:
        last = False
        cnt = module().tout.data(c[0])
        while not last:
            last = cnt == c[1]
            yield cnt, last
            cnt += 1


@alternative(qrange)
@gear(enablement=b'inclusive==False')
async def qrange_stop(stop: Integer, *, inclusive=False) -> Queue[b'stop']:
    cnt = stop.dtype(0)
    cur_cnt: stop.dtype
    last: Bool

    async with stop as s:
        last = False
        while not last:
            # while (cnt != s):
            cur_cnt = cnt
            cnt += 1

            last = cnt == s
            yield cur_cnt, last


@alternative(qrange)
@gear(enablement=b'inclusive==True')
async def qrange_stop_inclusive(stop: Integer, *, inclusive) -> Queue[b'stop']:
    cnt = stop.dtype(0)
    last: Bool

    async with stop as s:
        last = False
        while not last:
            last = cnt == s
            yield cnt, last
            cnt = code(cnt + 1, stop.dtype)
