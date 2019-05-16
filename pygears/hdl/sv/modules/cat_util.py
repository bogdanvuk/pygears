from pygears.typing import Queue
from pygears.hdl.templenv import isinput


def din_data_cat(intfs):
    data = []
    for intf in isinput(intfs):
        if issubclass(intf['type'], Queue):
            if int(intf['type'][0]) > 0:
                data.append(f'{intf["name"]}_s.data')
        else:
            if int(intf['type']) > 0:
                data.append(f'{intf["name"]}_s')

    return f'{{ {", ".join(reversed(data))} }}'
