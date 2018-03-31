import types
from pygears import gear, Queue, Tuple, Unit
from pygears.core.typing import TypingNamespacePlugin


@gear(enablement='issubclass({din}, Tuple)')
def flatten_tuple(din, *, lvl=1) -> 'flatten({din})':
    pass


@gear(alternatives=[flatten_tuple])
def flatten(din: Queue['{tdin}', '{din_lvl}'],
            *,
            lvl=1,
            dout_lvl='{din_lvl} - {lvl}') -> 'Queue[{tdin}, {dout_lvl}]':
    pass


def type_flatten(dtype, lvl=1):
    if issubclass(dtype, Queue):
        return Queue[dtype[0], dtype.lvl - lvl]
    elif issubclass(dtype, Tuple):

        lvl -= 1
        out_args = []
        for a in dtype.args:
            if lvl:
                a = type_flatten(a, lvl)

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


typing = types.SimpleNamespace(flatten=type_flatten)


class TypeExpandPlugin(TypingNamespacePlugin):
    @classmethod
    def bind(cls):
        cls.registry['TypeArithNamespace']['flatten'] = typing.flatten
