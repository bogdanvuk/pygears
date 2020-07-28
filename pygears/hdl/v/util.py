from pygears.typing import Int, Uint, is_type
from pygears.typing.visitor import TypingVisitorBase


class VGenTypeVisitor(TypingVisitorBase):
    def __init__(self, name, direction, basic_type='wire', hier=True):
        self.context = name
        self.basic_type = basic_type
        self.hier = hier
        self.direction = direction

    def visit_Int(self, type_, field, **kwds):
        return [
            f'{self.basic_type} signed [{type_.width-1}:0] {self.context}; // {type_}'
        ]

    def visit_Bool(self, type_, field, **kwds):
        return [f'{self.basic_type} [0:0] {self.context}; // {type_}']

    def visit_Uint(self, type_, field, **kwds):
        if type_.width != 0:
            return [
                f'{self.basic_type} [{type_.width-1}:0] {self.context}; // {type_}'
            ]

        return None

    visit_Ufixp = visit_Uint
    visit_Fixp = visit_Uint

    def visit_Unit(self, type_, field, **kwds):
        return None

    def visit_Union(self, type_, field, **kwds):
        res = []

        # top
        res.append(
            f'{self.basic_type} [{type_.width-1}:0] {self.context}; // {type_}')

        res.extend(
            self._complex_type_iterator([('data', type_.data),
                                         ('ctrl', type_.ctrl)]))

        return res

    def visit_Queue(self, type_, field, **kwds):
        res = []

        # top
        res.append(
            f'{self.basic_type} [{type_.width-1}:0] {self.context}; // {type_}')

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
                pos_high = pos_low + subt.width - 1
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

    def visit_Tuple(self, type_, field, **kwds):
        res = []
        res.append(
            f'{self.basic_type} [{type_.width-1}:0] {self.context}; // {type_}')

        res.extend(self._complex_type_iterator(zip(type_.fields, type_.args)))

        return res

    def visit_Array(self, type_, field, **kwds):
        if type_.data.signed:
            merge_t = Int[type_.data.width * len(type_)]
        else:
            merge_t = Uint[type_.data.width * len(type_)]

        arr_var = f'{self.context}_arr'
        res = self.visit(merge_t, type_.fields[0])
        res.append(
            f'{self.basic_type} [{type_.data.width-1}:0] {arr_var} [0:{int(len(type_))-1}];')

        high = 0
        low = 0
        for i in range(len(type_)):
            high += type_.data.width

            if self.direction == 'input':
                res.append(f'assign {arr_var}[{i}] = {self.context}[{high - 1}:{low}];')
            else:
                res.append(f'assign {self.context}[{high - 1}:{low}] = {arr_var}[{i}];')

            low += type_.data.width

        return res


def vgen_intf(dtype, name, direction, hier=True):
    valid = f'reg {name}_valid;\n'
    ready = f'reg {name}_ready;'

    if isinstance(dtype, str):
        data = f'{dtype} {name}_data;\n'
        return data + valid + ready

    if dtype.width == 0:
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

    if is_type(dtype) and dtype.width == 0:
        return f'{vtype} [0:0] {name};'

    if not hier:
        if is_type(dtype):
            width = dtype.width
            sign = 'signed' if getattr(dtype, 'signed', False) else ''
        elif isinstance(dtype, (tuple, list)):
            width = sum(d.width for d in dtype)
            sign = ''

        return f'{vtype} {sign} [{width-1}:0] {name}; // {dtype}'

    vis = VGenTypeVisitor(name,
                          basic_type=vtype,
                          direction=direction,
                          hier=hier)

    return '\n'.join(vis.visit(type_=dtype, field=name))
