from pygears.core.hier import Module
from pygears.core.module_def import ModuleDefinition
from pygears.typing.bool import Bool
from pygears.typing.tuple import Tuple
import pygears.typing.queue
from pygears.typing.base import param_subs


def arg_is_delim(t):
    if issubclass(t, Bool):
        return True

    if issubclass(t, Tuple):
        return all([arg_is_delim(a) for a in t])

    return False


def lvl_if_queue(t):
    if not issubclass(t, pygears.typing.queue.Queue):
        return 0
    else:
        return t.lvl


class Concat(Module):
    def __init__(self, func, *args, **kwds):
        super().__init__(func, *args, **kwds)

    # def __call__(self, *args, **kwargs):
    #     return super().__call__(*args, **kwargs)

    def resolve_types(self):
        super().resolve_types()

        is_queue = [lvl_if_queue(a.get_type()) for a in self.args]

        is_delim = [arg_is_delim(a.get_type()) for a in self.args]

        dout_type_names = [f'DIN{i}_WIDTH' for i in range(len(self.args))]

        dout_templates = []
        for name, isq, delim in zip(dout_type_names, is_queue, is_delim):
            if (not delim) or all(is_delim):
                dout_t = f'{{{name}}}'

                if isq and self.params['queue_pack'] and not any(is_delim):
                    dout_t += '[0]'

                dout_templates.append(dout_t)

        # dout_templates = [
        #     f'{{{name}}}' + ('[0]' if (isq and not any(is_delim)) else '')
        #     for name, isq, delim in zip(dout_type_names, is_queue, is_delim)
        #     if (not delim) or all(is_delim)
        # ]

        base_type_str = ','.join(dout_templates)

        # Check if concat should pack output in a Queue. This is done if:
        #    1. queue_pack parameter is set to True
        #    2. Only the last argument in concat is Queue delimiter
        #    3. One of the arguments is a Queue
        if self.params['queue_pack'] and (
                (is_delim[-1] and (not all(is_delim))) or any(is_queue)):

            queue_level = 1
            # If this is a functor for a multilevel list, the output should a
            # multilevel list
            if is_delim[-1]:
                delim_type = self.args[-1].get_type()

                if issubclass(delim_type, Tuple):
                    queue_level = len(delim_type.args)
            else:
                queue_level = max(is_queue)

            # How many inputs other than delimiters are concatenated?
            if len(dout_templates) == 1:
                type_str = f'{base_type_str}'
            else:
                type_str = f'Tuple[{base_type_str}]'

            # Wrap output data type in Queue of appropriate level
            type_str = f'Queue[{type_str}, {queue_level}]'

            # for i in range(queue_level):
            #     type_str = f'Queue[{type_str}]'

        else:
            # We are dealing with a simple concat, not involving Queues
            type_str = f'Tuple[{base_type_str}]'

        self.ftypes[-1] = param_subs(type_str, self.params, {})
        # print("    ", self.ftypes)


# cat = ModuleDefinition(Concat, concat)
# cat = ModuleDefinition(Concat, concat)()


def cat(*din, **kwargs):
    def cat(*din: '{{DIN{0}_WIDTH}}', queue_pack=True) -> '{To}':
        pass

    return ModuleDefinition(Concat, cat)(*din, **kwargs)
