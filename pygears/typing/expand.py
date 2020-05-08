from . import Queue, Tuple, Union, typeof


def next_pos(type_list, comb, t):
    if len(type_list) == 1:
        yield comb + [t]
    else:
        yield from type_comb_rec(type_list[:-1], comb + [t])


def type_comb_rec(type_list, comb):
    type_ = type_list[-1]
    if typeof(type_, Union):
        for t in type_.types:
            yield from next_pos(type_list, comb, t)
    else:
        yield from next_pos(type_list, comb, type_)


def tuple_type_comb(type_):
    type_list = [t for t in type_]

    for t in type_comb_rec(type_list, []):
        yield Tuple[tuple(reversed(t))]


def queue_type_comb(type_):
    # type_list = [t for t in type_[0]]
    for t in type_[0]:
        yield Queue[t, type_.lvl]

    # for t in type_comb_rec(type_list, []):
    #     yield Queue[tuple(reversed(t)), type_.lvl]


def expand(type_):
    if typeof(type_, Tuple):
        return Union[tuple(tuple_type_comb(type_))]
    elif typeof(type_, Queue):
        if typeof(type_[0], Tuple):
            return Tuple[tuple(queue_type_comb(type_))]
        elif typeof(type_[0], Union):
            utypes = [Queue[t, type_.lvl] for t in type_[0].types]
            return Union[tuple(utypes)]
    else:
        return type_
