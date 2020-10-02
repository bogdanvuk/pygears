from pygears.typing import Queue, typeof


def din_data_cat(intfs, order=None):

    if order is None:
        order = range(len(intfs))

    data = []
    for o in order:
        intf = intfs[o]

        if intf['modport'] == 'producer':
            continue

        if issubclass(intf['type'], Queue):
            if intf['type'][0].width > 0:
                data.append(f'{intf["name"]}_s.data')
        else:
            if intf['type'].width > 0:
                data.append(f'{intf["name"]}_s')

    return f'{{ {", ".join(reversed(data))} }}'


def din_data_cat_value(data):
    dout = []
    for d in data:
        if isinstance(d, Queue):
            dout.append(d.data)
        else:
            dout.append(d)

    return tuple(dout)
