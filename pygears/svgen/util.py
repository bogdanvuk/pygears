from pygears.typing.visitor import TypingVisitorBase
from pygears.typing import bitw


def svgen_visitor(cls):
    def svgen_action(top, conf):
        v = cls()
        v.conf = conf
        v.visit(top)
        return top

    return svgen_action


class SVGenTypeVisitor(TypingVisitorBase):
    struct_str = "typedef struct packed {"
    union_str = "typedef union packed {"

    def __init__(self, name, basic_type='logic'):
        self.struct_array = []
        self.context = name
        self.basic_type = basic_type
        self.depth = -1

    def visit(self, type_, field):
        self.depth += 1
        type_declaration = super().visit(type_, field)
        self.depth -= 1
        return type_declaration

    def visit_int(self, type_, field):
        if (not self.depth):
            self.struct_array.append(
                f'typedef {self.basic_type} signed [{int(type_)-1}:0] {self.context}_t; // {type_}\n'
            )
        return f'{self.basic_type} signed [{int(type_)-1}:0]'

    def visit_bool(self, type_, field):
        if (not self.depth):
            self.struct_array.append(
                f'typedef {self.basic_type} [0:0] {self.context}_t; // {type_}'
            )
        return f'{self.basic_type} [0:0]'

    def visit_uint(self, type_, field):
        if (int(type_) == 0):
            return None
        if (not self.depth):
            self.struct_array.append(
                f'typedef {self.basic_type} [{int(type_)-1}:0] {self.context}_t; // {type_}\n'
            )
        return f'{self.basic_type} [{int(type_)-1}:0]'

    def visit_unit(self, type_, field):
        return None

    def visit_union(self, type_, field):
        struct_fields = []
        max_len = 0
        high_parent_context = self.context
        middle_parent_context = f'{high_parent_context}_data'
        low_parent_context = f'{middle_parent_context}_data'

        for t in (type_.types):
            if (int(t) > max_len):
                max_len = int(t)

        # for t, f in zip(reversed(type_.args), reversed(type_.fields)):
        #     middle_type = Tuple[{f: t, 'dummy': Uint[max_len-int(t)]}]
        #     struct_fields.append(f'{self.struct_str}')
        #     for tp, fd in zip(reversed(middle_type.args), reversed(middle_type.fields)):
        #         self.context = f'{low_parent_context}_{fd}'
        #         type_declaration = self.visit(tp, fd)
        #         if (type_declaration is not None):
        #             struct_fields.append(f'    {type_declaration} {fd}; // {tp}')
        #     struct_fields.append(f'}} {middle_parent_context}_{f}_t;\n')

        for i, t in reversed(list(enumerate(type_.args))):
            field_tmp = f'f{i}'
            struct_fields.append(f'{self.struct_str} // ({t}, u?)')
            self.context = f'{low_parent_context}_{field_tmp}'
            type_declaration = self.visit(t, field_tmp)
            if (int(t) < max_len):
                struct_fields.append(
                    f'    {self.basic_type} [{max_len-int(t)-1}:0] dummy; // u{max_len-int(t)}'
                )
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
        struct_fields.append(f'    {middle_parent_context}_t data; // {type_}')
        struct_fields.append(f'}} {high_parent_context}_t;\n')

        self.struct_array.append('\n'.join(struct_fields))

        self.context = high_parent_context

        return f'{high_parent_context}_t'

    def visit_queue(self, type_, field):
        struct_fields = []
        parent_context = self.context
        struct_fields.append(f'{self.struct_str} // {type_}')
        struct_fields.append(
            f'    {self.basic_type} [{type_.args[1]-1}:0] eot; // u{type_.args[1]}'
        )
        self.context = f'{parent_context}_data'
        type_declaration = self.visit(type_.args[0], type_.fields[0])

        if (type_declaration is not None):
            struct_fields.append(
                f'    {type_declaration} data; // {type_.args[0]}')

        struct_fields.append(f'}} {parent_context}_t;\n')
        self.struct_array.append('\n'.join(struct_fields))

        self.context = parent_context

        return f'{parent_context}_t'

    def visit_tuple(self, type_, field):
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

    def visit_array(self, type_, field):
        if (not self.depth):
            struct_fields = []
            parent_context = self.context
            self.context = f'{parent_context}_data'

        type_declaration = self.visit(type_.args[0], type_.fields[0])
        split_type = type_declaration.split(" ", 1)
        split_type.insert(1, f'[{type_.args[1]-1}:0]')
        type_declaration = ' '.join(split_type)

        if (not self.depth):
            struct_fields.append(
                f'typedef {type_declaration} {parent_context}_t; // {type_}\n')
            self.struct_array.append('\n'.join(struct_fields))
            self.context = parent_context
            return f'{parent_context}_t'
        else:
            return f'{type_declaration}'


def svgen_typedef(dtype, name):
    if isinstance(dtype, str):
        return f'typedef {dtype} {name}_t;'
    elif int(dtype) == 0:
        return f'typedef logic [0:0] {name}_t;'

    vis = SVGenTypeVisitor(name)
    vis.visit(type_=dtype, field=name)
    return '\n'.join(vis.struct_array)
