from pygears.typing import Queue, typeof


def din_data_cat_v(intfs):
    data = []
    for intf in intfs:
        if intf['modport'] == 'producer':
            continue

        if issubclass(intf['type'], Queue):
            if int(intf['type'][0]) > 0:
                data.append(f'{intf["name"]}_s_data')
        else:
            if int(intf['type']) > 0:
                data.append(f'{intf["name"]}_s')

    return f'{{ {", ".join(reversed(data))} }}'


def din_data_cat(intfs):
    data = []
    for intf in intfs:
        if intf['modport'] == 'producer':
            continue

        if issubclass(intf['type'], Queue):
            if int(intf['type'][0]) > 0:
                data.append(f'{intf["name"]}_s.data')
        else:
            if int(intf['type']) > 0:
                data.append(f'{intf["name"]}_s')

    return f'{{ {", ".join(reversed(data))} }}'


def din_data_cat_value(data):
    dout = []
    for d in data:
        if isinstance(d, Queue):
            if int(type(d.data)) > 0:
                dout.append(d.data)
        else:
            if int(type(d)) > 0:
                dout.append(d)

    return tuple(dout)
