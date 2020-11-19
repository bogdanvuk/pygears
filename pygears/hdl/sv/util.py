from pygears.typing.visitor import TypingVisitorBase
from pygears.typing import bitw, is_type


class SVGenTypeVisitor(TypingVisitorBase):
    struct_str = "typedef struct packed {"
    union_str = "typedef union packed {"

    def __init__(self, name, basic_type='logic', depth=4):
        self.struct_array = []
        self.context = name
        self.basic_type = basic_type
        self.max_depth = depth
        self.depth = -1

    def visit(self, type_, field):
        if self.depth >= self.max_depth:
            return f'{self.basic_type} [{type_.width-1}:0]'

        self.depth += 1
        type_declaration = super().visit(type_, field)
        self.depth -= 1
        return type_declaration

    def visit_Int(self, type_, field):
        if (not self.depth):
            self.struct_array.append(
                f'typedef {self.basic_type} signed [{type_.width-1}:0] {self.context}_t; // {type_}\n')
        return f'{self.basic_type} signed [{type_.width-1}:0]'

    def visit_Bool(self, type_, field):
        if (not self.depth):
            self.struct_array.append(
                f'typedef {self.basic_type} {self.context}_t; // {type_}')
        return f'{self.basic_type}'

    def visit_Uint(self, type_, field):
        if (type_.width == 0):
            return None
        if (not self.depth):
            self.struct_array.append(
                f'typedef {self.basic_type} [{type_.width-1}:0] {self.context}_t; // {type_}\n')
        return f'{self.basic_type} [{type_.width-1}:0]'

    visit_Ufixp = visit_Uint
    visit_Fixp = visit_Int

    def visit_Unit(self, type_, field):
        return None

    def visit_Union(self, type_, field):
        struct_fields = []
        max_len = 0
        high_parent_context = self.context
        middle_parent_context = f'{high_parent_context}_data'
        low_parent_context = f'{middle_parent_context}_data'

        for t in (type_.types):
            if (t.width > max_len):
                max_len = t.width

        # if self.depth < self.max_depth:
        if False:
            for i, t in reversed(list(enumerate(type_.args))):
                field_tmp = f'f{i}'
                struct_fields.append(f'{self.struct_str} // ({t}, u?)')
                self.context = f'{low_parent_context}_{field_tmp}'
                type_declaration = self.visit(t, field_tmp)
                if (t.width < max_len):
                    struct_fields.append(
                        f'    {self.basic_type} [{t.width-1}:0] dummy; // u{t.width}')
                if (type_declaration is not None):
                    struct_fields.append(f'    {type_declaration} {field_tmp}; // {t}')
                struct_fields.append(f'}} {middle_parent_context}_{field_tmp}_t;\n')

            # create union
            struct_fields.append(f'{self.union_str} // {type_}')
            for i, t in reversed(list(enumerate(type_.args))):
                field_tmp = f'f{i}'
                struct_fields.append(
                    f'    {middle_parent_context}_{field_tmp}_t {field_tmp}; // ({t}, u?)')
            struct_fields.append(f'}} {middle_parent_context}_t;\n')

        # create struct
        struct_fields.append(f'{self.struct_str} // {type_}')
        struct_fields.append(
            f'    {self.basic_type} [{bitw(len(type_.args)-1)-1}:0] ctrl; // u{bitw(len(type_.args)-1)}'
        )

        if type_.data.width > 0:
            struct_fields.append(
                f'    {self.basic_type} [{type_.data.width-1}:0] data; // {type_.data}')

        struct_fields.append(f'}} {high_parent_context}_t;\n')

        self.struct_array.append('\n'.join(struct_fields))

        self.context = high_parent_context

        return f'{high_parent_context}_t'

    def visit_Queue(self, type_, field):
        struct_fields = []
        parent_context = self.context
        struct_fields.append(f'{self.struct_str} // {type_}')
        struct_fields.append(
            f'    {self.basic_type} [{type_.args[1]-1}:0] eot; // u{type_.args[1]}')
        self.context = f'{parent_context}_data'
        type_declaration = self.visit(type_.args[0], type_.fields[0])

        if (type_declaration is not None):
            struct_fields.append(f'    {type_declaration} data; // {type_.args[0]}')

        struct_fields.append(f'}} {parent_context}_t;\n')
        self.struct_array.append('\n'.join(struct_fields))

        self.context = parent_context

        return f'{parent_context}_t'

    def visit_Tuple(self, type_, field):
        if self.depth == self.max_depth:
            return self.visit_Uint(type_, field)

        struct_fields = []
        parent_context = self.context

        struct_fields.append(f'{self.struct_str} // {type_}')
        for t, f in zip(reversed(type_.args), reversed(type_.fields)):
            self.context = f'{parent_context}_{f}'
            type_declaration = self.visit(t, f)
            if type_declaration:
                struct_fields.append(f'    {type_declaration} {f}; // {t}')

        struct_fields.append(f'}} {parent_context}_t;\n')
        self.struct_array.append('\n'.join(struct_fields))

        self.context = parent_context

        return f'{parent_context}_t'

    def visit_Array(self, type_, field):
        if not self.depth:
            struct_fields = []
            parent_context = self.context
            self.context = f'{parent_context}_data'

        type_declaration = self.visit(type_.args[0], type_.fields[0])

        split_type = type_declaration.split(" ")
        if 'signed' in split_type:
            insert_idx = split_type.index('signed') + 1
        else:
            insert_idx = 1

        split_type.insert(insert_idx, f'[{int(type_.args[1])-1}:0]')
        type_declaration = ' '.join(split_type)

        if not self.depth:
            struct_fields.append(
                f'typedef {type_declaration} {parent_context}_t; // {type_}\n')
            self.struct_array.append('\n'.join(struct_fields))
            self.context = parent_context
            return f'{parent_context}_t'

        return f'{type_declaration}'


def svgen_typedef(dtype, name, depth=4):
    # TODO: if a variable is called "wr", of the type that has a composite
    # field "data", than struct for that field will be called "wr_data_t". If
    # there is a variable "wr_data" in same module, it will also have the type
    # called "wr_data_t". This can be in conflict when the type definitions are
    # added for verilator debugging. Maybe think of a different scheme to name
    # subtypes
    if isinstance(dtype, str):
        return f'typedef {dtype} {name}_t;'

    assert is_type(dtype)

    if dtype.width == 0:
        return f'typedef logic [0:0] {name}_t;'

    vis = SVGenTypeVisitor(name, depth=depth)
    vis.visit(type_=dtype, field=name)
    return '\n'.join(vis.struct_array)
