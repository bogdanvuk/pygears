from pygears.lib import drv, collect, mon
import inspect
from pygears.sim import sim
from pygears.typing import Integer, Int, Uint, is_type, typeof, Any
from pygears.core.partial import extract_arg_kwds, combine_arg_kwds, all_args_specified
from pygears.core.gear_inst import resolve_args
from pygears import reset, clear
from pygears.sim import cosim


def infer_dtype(val, dtype):
    if is_type(type(val)):
        return type(val)

    if not is_type(dtype) or typeof(dtype, Any):
        if isinstance(val, int):
            if val < 0:
                return type(Int(val))
            else:
                return type(Uint(val))

    if dtype.specified:
        return dtype

    return type(dtype.base(val))


def call(f, *args, **kwds):
    clear()
    kwd_intfs, kwd_params = extract_arg_kwds(kwds, f)
    args_comb = combine_arg_kwds(args, kwd_intfs, f)

    paramspec = inspect.getfullargspec(f.func)
    args, annotations = resolve_args(args_comb, paramspec.args,
                                     paramspec.annotations, paramspec.varargs)

    dtypes = [infer_dtype(args[arg], annotations[arg]) for arg in args]

    seqs = [drv(t=t, seq=[v]) for t, v in zip(dtypes, args_comb)]

    outputs = f(*seqs, **kwd_params)

    if isinstance(outputs, tuple):
        res = [[] for _ in outputs]

        for o, r in zip(outputs, res):
            collect(o | mon, result=r)
    else:
        res = [[]]
        collect(outputs | mon, result=res[0])

    sim(check_activity=False)

    if isinstance(outputs, tuple):
        return res
    else:
        return res[0]
