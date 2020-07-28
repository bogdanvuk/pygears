from pygears.typing import Queue
from pygears.hdl.templenv import isinput


def din_data_cat(intfs):
    data = []
    for intf in isinput(intfs):
        if issubclass(intf['type'], Queue):
            if intf['type'][0].width > 0:
                data.append(f'{intf["name"]}_s.data')
        else:
            if intf['type'].width > 0:
                data.append(f'{intf["name"]}_s')

    return f'{{ {", ".join(reversed(data))} }}'
