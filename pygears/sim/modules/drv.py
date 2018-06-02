import inspect

from pygears import gear
from pygears.typing import TLM


class TypingYieldVisitorBase:
    def visit(self, data, dtype):
        visit_func_name = f'visit_{dtype.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)
        ret = visit_func(data, dtype)
        if inspect.isgenerator(ret):
            yield from ret
        else:
            yield ret

    def visit_default(self, data, dtype):
        yield data


def pack_data(self, lvl, dtype, d):
    out = 0
    for bit in lvl:
        out = (out << 1) | bit

    out = (out << int(dtype[0])) | d
    return d


class TypeDrvVisitor(TypingYieldVisitorBase):
    def visit_uint(self, data, dtype):
        mask = ((1 << int(dtype)) - 1)
        return data & mask

    def visit_queue(self, data, dtype):
        for i, d in enumerate(data):
            for ret in self.visit(d, dtype[:-1]):
                if i == len(data) - 1:
                    ret |= 1 << (int(dtype) - 1)

                yield ret

    def visit_tuple(self, data, dtype):
        ret = 0
        for d, t in zip(reversed(data), reversed(dtype)):
            elem = next(self.visit(d, t))
            ret <<= int(t)
            ret |= elem

        return ret


@gear
async def drv(din: TLM['t'], *, t=b't') -> b't':
    item = await din.get()
    print("Driver got: ", item)

    for d in TypeDrvVisitor().visit(item, t):
        print('Driver sends: ', d)
        yield d

    print("Driver done")
    din.task_done()
