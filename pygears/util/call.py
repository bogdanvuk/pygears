from pygears.lib import drv, collect, mon
from pygears.sim import sim
from pygears.typing import Integer, Int, Uint, is_type
from pygears.core.partial import extract_arg_kwds, combine_arg_kwds, all_args_specified


def infer_dtype(val):
    if is_type(type(val)):
        return type(val)

    if isinstance(val, int):
        if val < 0:
            return type(Int(val))
        else:
            return type(Uint(val))


def call(f, *args, **kwds):
    kwd_intfs, kwd_params = extract_arg_kwds(kwds, f)
    args_comb = combine_arg_kwds(args, kwd_intfs, f)
    dtypes = [infer_dtype(arg) for arg in args_comb]

    seqs = [drv(t=t, seq=[v]) for t, v in zip(dtypes, args_comb)]

    outputs = f(*seqs, **kwd_params)

    if isinstance(outputs, tuple):
        res = [[] for _ in outputs]

        for o, r in zip(outputs, res):
            collect(o | mon, result=r)
    else:
        res = [[]]
        collect(outputs | mon, result=res[0])

    mod = seqs[0].consumers[0].gear
    from pygears.sim import cosim
    # cosim('/qround', 'verilator')
    cosim(mod, 'verilator')
    sim(check_activity=False)

    if isinstance(outputs, tuple):
        return res
    else:
        return res[0]
