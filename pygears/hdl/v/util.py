from pygears.hls.utils import add_to_list
from pygears.typing import Int, Uint, typeof
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
            f'{self.basic_type} [{int(type_)-1}:0] {self.context}; // {type_}'
        )

        res.extend(self._complex_type_iterator(zip(type_.fields, type_.args)))

        return res

    def visit_array(self, type_, field, **kwds):
        if typeof(type_.args[0], Int):
            merge_t = Int[int(type_.args[0]) * len(type_)]
        elif typeof(type_.args[0], Uint):
            merge_t = Uint[int(type_.args[0]) * len(type_)]
        else:
            raise Exception('Array subtype can only be Uint or Int in Verilog')
        merge = self.visit(merge_t, type_.fields[0])
        assert len(merge) == 1

        res = []
        high = 0
        low = 0
        res.append(f'{merge[0]} // from {type_}')
        for i in range(len(type_)):
            name = f'{self.context}_{i}'
            high += int(type_.args[0])

            sub = self.visit(type_.args[0], type_.fields[0])
            assert len(sub) == 1
            sub_var = sub[0].split(';', 1)[0]  # remove ; // comment
            sub_var = sub_var.rsplit(' ', 1)[0]  # remove name
            sub_var += f' {name}; // {type_.args[0]}'
            res.append(sub_var)
            if self.direction == 'input':
                res.append(
                    f'assign {name} = {self.context}[{high - 1}:{low}];')
            else:
                res.append(
                    f'assign {self.context}[{high - 1}:{low}] = {name};')
            low += int(type_.args[0])

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


def vgen_reg(dtype, name, direction, hier=True):
    if isinstance(dtype, str):
        return f'{dtype} {name};'

    if int(dtype) == 0:
        return f'reg [0:0] {name};'

    if not hier:
        return f'reg [{int(dtype)-1}:0] {name}; // {dtype}'

    vis = VGenTypeVisitor(name,
                          basic_type='reg',
                          direction=direction,
                          hier=hier)

    return '\n'.join(vis.visit(type_=dtype, field=name))


def vgen_wire(dtype, name, direction, hier=True):
    if isinstance(dtype, str):
        return f'{dtype} {name};'

    if int(dtype) == 0:
        return f'wire [0:0] {name};'

    if not hier:
        return f'wire [{int(dtype)-1}:0] {name}; // {dtype}'

    vis = VGenTypeVisitor(name,
                          basic_type='wire',
                          direction=direction,
                          hier=hier)
    return '\n'.join(vis.visit(type_=dtype, field=name))
