from . import Queue, Tuple, Unit


def flatten(dtype, lvl=1):
    if issubclass(dtype, Queue):
        return Queue[dtype[0], dtype.lvl - lvl]
    elif issubclass(dtype, Tuple):

        lvl -= 1
        out_args = []
        for a in dtype.args:
            if lvl:
                a = flatten(a, lvl)

            if issubclass(a, Tuple):
                out_args.extend(a.args)
            elif a != Unit:
                out_args.append(a)

        if len(out_args) == 0:
            return Unit
        elif len(out_args) == 1:
            return out_args[0]
        else:
            return Tuple[tuple(out_args)]
    else:
        return dtype
