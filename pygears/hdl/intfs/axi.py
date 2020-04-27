import typing
from pygears.typing import Queue, Union, typeof, Tuple
from pygears.typing.math import ceil_chunk, ceil_pow2
from dataclasses import dataclass, field

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


@dataclass
class AxiPortConf:
    parent: str
    t: str
    port: typing.Any = None
    datamap: typing.Any = None
    params: dict = field(default_factory=dict)

    @property
    def name(self):
        return self.port.basename


@dataclass
class AxiIntfConf:
    name: str
    t: str
    comp: typing.Dict[str, AxiPortConf] = field(default_factory=dict)

    @property
    def direction(self):
        d = ''

        if 'wdata' in self.comp:
            d += 'w'

        if 'rdata' in self.comp:
            d += 'r'

        return d


def port_conf(parent, type_, p, datamap=None):
    conf = AxiPortConf(parent, type_, p, datamap)

    if datamap:
        width = p.dtype[datamap].width
    else:
        width = p.dtype.width

    if type_ in ['wdata', 'rdata']:
        width = ceil_chunk(ceil_pow2(width), 32)

    if type_ == 'wdata':
        conf.params = {'wdata': width, 'wstrb': width // 8}
    else:
        conf.params = {type_: width}

    return conf


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

    if p.direction == axi_dir and subintf not in ['araddr', 'awaddr', 'wdata']:
        raise Exception(
            f'Cannot drive gear port {name} from AXi port {axi_name}.{subintf}')

    if p.direction != axi_dir and subintf not in ['rdata']:
        raise Exception(
            f'Cannot drive AXi port {axi_name}.{subintf} from gear port {name}')

    if subintf == 'awaddr':
        if typeof(p.dtype, Tuple) and axi_conf.get('wdata', '') == name:
            return port_conf(axi_conf['type'], subintf, p, slice(0, 1))

    if subintf == 'wdata':
        if typeof(p.dtype, Tuple) and axi_conf.get('awaddr', '') == name:
            return port_conf(axi_conf['type'], subintf, p, slice(1, 2))

    return port_conf(axi_conf['type'], subintf, p)


def get_axi_conf(top, conf):
    axi_port_cfg = {}

    for name, pconf in conf.items():
        if pconf['type'] not in ['axi', 'axidma']:
            continue

        axi_port_cfg[name] = AxiIntfConf(name, pconf['type'])
        for subintf in ['araddr', 'rdata', 'awaddr', 'wdata']:
            if subintf not in pconf:
                continue

            axi_port_cfg[name].comp[subintf] = get_port_def(
                top, pconf[subintf], name, subintf, pconf)

    for name, p in axi_port_cfg.copy().items():
        if p.t in ['axidma']:
            p.comp['araddr'] = AxiPortConf(p.t, 'araddr', params={'araddr': 32})

            axil_comp = {
                'awaddr': AxiPortConf('axilite', 'awaddr', params={'awaddr': 5}),
                'wdata':
                AxiPortConf('axilite', 'wdata', params={
                    'wdata': 32,
                    'wstrb': 4
                }),
                'araddr': AxiPortConf('axilite', 'araddr', params={'araddr': 5}),
                'rdata': AxiPortConf('axilite', 'rdata', params={'rdata': 32}),
                'bresp': AxiPortConf('axilite', 'bresp', params={'bresp': True})
            }

            axi_port_cfg[f'{name}_ctrl'] = AxiIntfConf(f'{name}_ctrl', 'axilite', axil_comp)

        if p.t in ['axi']:
            if 'wdata' in p.comp and not 'awaddr' in p.comp:
                p.comp['awaddr'] = AxiPortConf(p.t, 'awaddr', params={'awaddr': 1})

            if 'rdata' in p.comp and not 'araddr' in p.comp:
                p.comp['araddr'] = AxiPortConf(p.t, 'araddr', params={'araddr': 1})

            if 'wdata' in p.comp and 'bresp' not in p.comp:
                p.comp['bresp'] = AxiPortConf(
                    p.t, 'bresp', params={'bresp': 'awaddr' in p.comp})

        # elif p.t == 'axis':
        #     if p['direction'] == 'in':
        #         tmplt = axi_intfs.AXIS_SLAVE
        #     else:
        #         tmplt = axi_intfs.AXIS_MASTER

        #     pdefs = axi_intfs.port_def(tmplt, name, data=p['width'], last=p['w_eot'] > 0)

        #     defs.extend(pdefs)

    print(axi_port_cfg)
    return axi_port_cfg
