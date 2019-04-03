import pprint
from ..typing import Tuple


def pprint_Tuple(printer, object, stream, indent, allowance, context, level):
    if printer._compact:
        if not hasattr(object, '__parameters__'):
            printer._format(
                tuple(object.args), stream, indent, allowance, context,
                level - 1)
        else:
            printer._format(
                dict(zip(object.fields, object.args)), stream, indent,
                allowance, context, level - 1)

    else:
        stream.write('Tuple')

        cur_indent = ((level - 1) * printer._indent_per_level)
        sub_indent = (level * printer._indent_per_level)

        if object.args:
            stream.write('[')
            if not hasattr(object, '__parameters__'):
                stream.write('\n' + ' ' * (cur_indent + 1))
                repr_obj = object.args
                printer._format_items(repr_obj, stream, cur_indent,
                                      allowance + 2, context, level)
                stream.write('\n' + ' ' * cur_indent)
            else:
                stream.write('{\n' + ' ' * sub_indent)
                repr_obj = list(zip(object.fields, object.args))
                printer._format_dict_items(repr_obj, stream, cur_indent,
                                           allowance + 2, context, level)
                stream.write('\n' + ' ' * cur_indent + '}')
            stream.write(']')


pprint.PrettyPrinter._dispatch[type(Tuple).__repr__] = pprint_Tuple
