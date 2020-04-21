from pygears.typing import Queue, Union, typeof, Tuple
from pygears.typing.math import ceil_chunk, ceil_pow2

    # axi_port_cfg = conf.copy()

    # port_map = {}
    # for p in top.in_ports + top.out_ports:
    #     dtype = p.dtype
    #     w_data = int(dtype)
    #     w_eot = 0
    #     w_addr = 0
    #     if typeof(dtype, Queue):
    #         w_data = int(dtype.data)
    #         w_eot = int(dtype.eot)
    #         width = ceil_chunk(ceil_pow2(int(w_data)), 32)
    #     else:
    #         width = ceil_chunk(w_data, 8)

    #     port_cfg = {
    #         'width': width,
    #         'w_data': w_data,
    #         'w_eot': w_eot,
    #         'w_addr': w_addr,
    #         'name': p.basename,
    #         'dir': p.direction
    #     }
    #     port_map[p.basename] = port_cfg

def port_conf(width, p):
    return {
        'width': width,
        'name': p.basename,
        'dir': p.direction
    }

def get_port_def(top, name, axi_name, subintf, axi_conf):
    if axi_conf['type'] == 'axi':
        axi_dir = 'in'
    elif axi_conf['type'] == 'axidma':
        axi_dir = 'out'
    else:
        raise Exception

    for p in top.in_ports + top.out_ports:
        if p.basename == name:
            break
    else:
        breakpoint()
        raise Exception(
            f'Port "{name}" supplied for {subintf} port of the'
            f' {axi_name} interface, not found')

    if p.direction == axi_dir and subintf not in ['raddr', 'waddr', 'wdata']:
        raise Exception(f'Cannot drive gear port {name} from AXi port {axi_name}.{subintf}')

    if p.direction != axi_dir and subintf not in ['rdata']:
        raise Exception(f'Cannot drive AXi port {axi_name}.{subintf} from gear port {name}')

    if subintf == 'waddr':
        if typeof(p.dtype, Tuple) and axi_conf.get('wdata', '') == name:
            return port_conf(p.dtype[0].width, p)
        else:
            return port_conf(p.dtype.width, p)

    if subintf == 'wdata':
        if typeof(p.dtype, Tuple) and axi_conf.get('waddr', '') == name:
            return port_conf(p.dtype[1].width, p)
        else:
            return port_conf(p.dtype.width, p)

    if subintf == 'raddr':
        return port_conf(p.dtype.width, p)

    if subintf == 'rdata':
        return port_conf(p.dtype.width, p)


def get_axi_conf(top, conf):
    axi_port_cfg = {}

    for name, pconf in conf.items():
        if pconf['type'] not in ['axi', 'axidma']:
            continue

        axi_port_cfg[name] = {'type': pconf['type']}
        for subintf in ['raddr', 'rdata', 'waddr', 'wdata']:
            if subintf not in pconf:
                continue

            axi_port_cfg[name][subintf] = get_port_def(top, pconf[subintf], name, subintf, pconf)

    return axi_port_cfg
