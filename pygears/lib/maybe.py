from pygears import gear
from pygears.lib.union import ucase, select
from pygears.lib.ccat import ccat
from pygears.lib.const import fix
from pygears.lib.filt import filt
from pygears.lib.fmaps.union import unionmap
from pygears.typing import Maybe, cast, Bool


@gear
def resolve(din: Maybe, *, val):
    val = din.dtype.types[1](val)
    return din | ucase(f=(fix(val=val), None))


@gear
def apply(din: Maybe, *, f, args=None, balance=None):
    maybe_args = []
    maybe_kwds = {}

    if isinstance(args, (list, tuple)):
        for a in args:
            maybe_args.append(sync_with(din, a))
    elif isinstance(args, dict):
        for n, v in args.items():
            maybe_kwds[n] = sync_with(din, v)

    if maybe_args or maybe_kwds:
        dout = din | when_some | f(*maybe_args, **maybe_kwds)
    else:
        dout = din | when_some | f

    if balance is not None:
        ctrl = din['ctrl'] | balance
    else:
        ctrl = din['ctrl']

    return select(ctrl, Maybe[dout.dtype](), some(dout))


@gear
def sync_with(sync_in: Maybe, din, *, fcat=ccat, balance=None):
    return fcat(din, sync_in[1]) | Maybe | filt


@gear
def some(din) -> Maybe['din']:
    return ccat(din, Bool(True)) >> Maybe[din.dtype]


@gear
def when_some(din: Maybe) -> b'din.dtype':
    return din | filt(fixsel=1)
