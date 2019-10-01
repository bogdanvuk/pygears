from pygears.hls.utils import add_to_list
from pygears.typing import Int, Uint, typeof, is_type
from pygears.typing.visitor import TypingVisitorBase


class VGenTypeVisitor(TypingVisitorBase):
    def __init__(self, name, direction, basic_type='wire', hier=True):
        self.context = name
        self.basic_type = basic_type
        self.hier = hier
        self.direction = direction

    def visit_int(self, type_, field, **kwds):
        return [
            f'{self.basic_type} signed [{int(type_)-1}:0] {self.context}; // {type_}'
        ]

    def visit_bool(self, type_, field, **kwds):
        return [f'{self.basic_type} [0:0] {self.context}; // {type_}']

    def visit_uint(self, type_, field, **kwds):
        if int(type_) != 0:
            return [
                f'{self.basic_type} [{int(type_)-1}:0] {self.context}; // {type_}'
            ]

        return None

    visit_ufixp = visit_uint
    visit_fixp = visit_uint

    def visit_unit(self, type_, field, **kwds):
        return None

    def visit_union(self, type_, field, **kwds):
        res = []

        # top
        res.append(
            f'{self.basic_type} [{int(type_)-1}:0] {self.context}; // {type_}')

        res.extend(
            self._complex_type_iterator([('data', type_.data),
                                         ('ctrl', type_.ctrl)]))

        return res

    def visit_queue(self, type_, field, **kwds):
        res = []

        # top
        res.append(
            f'{self.basic_type} [{int(type_)-1}:0] {self.context}; // {type_}')

        res.extend(
            self._complex_type_iterator([('data', type_.data),
                                         ('eot', type_.eot)]))
        return res

    def _complex_type_iterator(self, subt_enum):
        if not self.hier:
            return []

        res = []
        parent_context = self.context
        pos_low = 0
        for name, subt in subt_enum:
            self.context = f'{parent_context}_{name}'
            sub_wire = self.visit(subt, None)
            if sub_wire:
                res.extend(sub_wire)
                pos_high = pos_low + int(subt) - 1
                if self.direction == 'input':
                    res.append(
                        f'assign {self.context} = {parent_context}[{pos_high}:{pos_low}];'
                    )
                else:
                    res.append(
                        f'assign {parent_context}[{pos_high}:{pos_low}] = {self.context};'
                    )

                pos_low = pos_high + 1

        self.context = parent_context
        return res

    def visit_tuple(self, type_, field, **kwds):
        res = []
        res.append(
            f'{self.basic_type} [{int(type_)-1}:0] {self.context}; // {type_}')

        res.extend(self._complex_type_iterator(zip(type_.fields, type_.args)))

        return res

    def visit_array(self, type_, field, **kwds):
        if type_.data.signed:
            merge_t = Int[int(type_.data) * len(type_)]
        else:
            merge_t = Uint[int(type_.data) * len(type_)]

        arr_var = f'{self.context}_arr'
        res = self.visit(merge_t, type_.fields[0])
        res.append(
            f'wire [{int(type_.data)-1}:0] {arr_var} [0:{int(len(type_))-1}];')

        high = 0
        low = 0
        for i in range(len(type_)):
            high += int(type_.data)
            res.append(f'assign {arr_var}[{i}] = {self.context}[{high - 1}:{low}];')
            low += int(type_.data)

        return res


def vgen_intf(dtype, name, direction, hier=True):
    valid = f'reg {name}_valid;\n'
    ready = f'reg {name}_ready;'

    if isinstance(dtype, str):
        data = f'{dtype} {name}_data;\n'
        return data + valid + ready

    if int(dtype) == 0:
        data = f'wire [0:0] {name}_data;\n'
        return data + valid + ready

    vis = VGenTypeVisitor(name,
                          direction=direction,
                          basic_type='wire',
                          hier=hier)
    data = '\n'.join(vis.visit(type_=dtype, field=name)) + '\n'
    return data + valid + ready


def vgen_signal(dtype, vtype, name, direction, hier=True):
    if isinstance(dtype, str):
        return f'{dtype} {name};'

    if is_type(dtype) and int(dtype) == 0:
        return f'{vtype} [0:0] {name};'

    if not hier:
        if is_type(dtype):
            width = int(dtype)
            sign = 'signed' if getattr(dtype, 'signed', False) else ''
        elif isinstance(dtype, (tuple, list)):
            width = sum(int(d) for d in dtype)
            sign = ''

        return f'{vtype} {sign} [{width-1}:0] {name}; // {dtype}'

    vis = VGenTypeVisitor(name,
                          basic_type=vtype,
                          direction=direction,
                          hier=hier)

    return '\n'.join(vis.visit(type_=dtype, field=name))
