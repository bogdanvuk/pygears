from . import Queue, Tuple, Union, typeof


def factor(type_):
    if typeof(type_, Union):
        for t in type_.types:
            if not typeof(t, Queue):
                return type_
        else:
            union_types = []
            for t in type_.types:
                union_types.append(t[0])
                lvl = t.lvl

            return Queue[Union[tuple(union_types)], lvl]
    elif typeof(type_, Tuple):
        if all(typeof(t, Queue) for t in type_):
            tuple_types = [t[0] for t in type_]
            return Queue[Tuple[tuple(tuple_types)], type_[0].lvl]
    else:
        return type_
