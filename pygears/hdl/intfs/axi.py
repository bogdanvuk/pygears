import typing
from pygears.typing import Queue, Union, typeof, Tuple
from pygears.typing.math import ceil_chunk, ceil_pow2, bitw, ceil_div
from dataclasses import dataclass, field


def index_to_sv_slice(dtype, key):
    subtype = dtype[key]

    if isinstance(key, str):
        key = dtype.fields.index(key)

    if isinstance(key, slice):
        key = min(key.start, key.stop)

    if key is None or key == 0:
        low_pos = 0
    else:
        low_pos = dtype[:key].width

    high_pos = low_pos + subtype.width - 1

    return f'{high_pos}:{low_pos}'


@dataclass
class AxiPortConf:
    parent: str
    t: str
    port: typing.Any = None
    datamap: typing.Any = None
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.parent, AxiIntfConf):
            id_param_name = f'C_AXI_{self.parent.name.upper()}_ID_WIDTH - 1'
            if self.t == 'araddr':
                self.params['arid'] = id_param_name
            elif self.t == 'awaddr':
                self.params['awid'] = id_param_name
            elif self.t == 'rdata':
                self.params['rid'] = id_param_name
            elif self.t == 'bresp':
                self.params['bid'] = id_param_name

    def dataslice(self, signal):
        if not self.datamap:
            return f'{self.port.dtype.width-1}:0'

        if not isinstance(self.datamap, dict):
            return index_to_sv_slice(self.port.dtype, self.datamap)

        return index_to_sv_slice(self.port.dtype, self.datamap[signal])

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

        if self.t == 'axis' and 'tdata' in self.comp:
            if self.comp['tdata'].port.direction == 'in':
                d += 'w'
            else:
                d += 'r'

        return d


def apply_key(key, dtype):
    if isinstance(key, tuple):
        for k in key:
            dtype = dtype[k]

    else:
        dtype = dtype[key]

    return dtype


def port_conf(parent, type_, p, datamap=None):
    if datamap is None:
        if not typeof(p.dtype, Queue) or type_ not in ['wdata', 'rdata', 'tdata']:
            width = p.dtype.width
        else:
            width = p.dtype['data'].width
            if type_ == 'rdata':
                datamap = {'rdata': 'data', 'rlast': 'eot'}
            elif type_ == 'wdata':
                datamap = {'wdata': 'data', 'wlast': 'eot'}
            elif type_ == 'tdata':
                datamap = {'tdata': 'data', 'tlast': 'eot'}

    else:
        key = datamap
        if isinstance(key, dict):
            key = key[type_]

        dtype = apply_key(key, p.dtype)

        width = dtype.width

    if type_ in ['wdata', 'rdata']:
        width = ceil_chunk(ceil_pow2(width), 32)
    elif type_ == 'tdata':
        width = ceil_chunk(ceil_pow2(width), 8)

    conf = AxiPortConf(parent, type_, p, datamap)

    if type_ == 'wdata':
        conf.params['wdata'] = width
        conf.params['wstrb'] = width // 8
    else:
        conf.params[type_] = width

    if type_ == 'tdata' and datamap and 'tlast' in datamap:
        conf.params['tlast'] = p.dtype.eot.width

    return conf


def get_port_def(top, name, axi_name, subintf, parent, axi_conf):
    for p in top.in_ports + top.out_ports:
        if p.basename == name:
            break
    else:
        breakpoint()
        raise Exception(
            f'Port "{name}" supplied for {subintf} port of the'
            f' {axi_name} interface, not found')

    if axi_conf['type'] == 'axi':
        if p.direction == 'in' and subintf not in ['araddr', 'awaddr', 'wdata']:
            raise Exception(
                f'Cannot drive gear port {name} from AXi port {axi_name}.{subintf}')

        if p.direction == 'out' and subintf not in ['rdata']:
            raise Exception(
                f'Cannot drive AXi port {axi_name}.{subintf} from gear port {name}')

    if subintf == 'awaddr':
        if typeof(p.dtype, Tuple) and axi_conf.get('wdata', '') == name:
            return port_conf(parent, subintf, p, 0)

    if subintf == 'araddr':
        if typeof(p.dtype, Tuple) and axi_conf.get('wdata', '') == name:
            return port_conf(parent, subintf, p, 0)

    if subintf == 'wdata':
        if typeof(p.dtype, Tuple) and axi_conf.get('awaddr', '') == name:
            if typeof(p.dtype[1], Union) and axi_conf.get('araddr', '') == name:
                return port_conf(parent, subintf, p, (1, 0))
            else:
                return port_conf(parent, subintf, p, 1)

    return port_conf(parent, subintf, p)


def port_by_name(top, name):
    for p in top.in_ports + top.out_ports:
        if p.basename == name:
            return p

    return None


def get_axi_conf(top, conf):
    axi_port_cfg = {}

    for name, pconf in conf.items():
        if isinstance(pconf, str):
            p = port_by_name(top, name)
            if p is None:
                raise Exception(f'Port "{name}" not found in the module')

            if p.direction == 'in':
                if pconf == 'axi':
                    pconf = {'type': pconf, 'wdata': name}
                elif pconf == 'axidma':
                    pconf = {'type': pconf, 'rdata': name}
                elif pconf == 'axis':
                    pconf = {'type': pconf, 'tdata': name}

            elif p.direction == 'out':
                if pconf == 'axi':
                    pconf = {'type': pconf, 'rdata': name}
                elif pconf == 'axidma':
                    pconf = {'type': pconf, 'wdata': name}
                elif pconf == 'axis':
                    pconf = {'type': pconf, 'tdata': name}

        if pconf['type'] not in ['axi', 'axidma', 'bram', 'axis']:
            continue

        if pconf['type'] in ['axi', 'axidma', 'bram']:
            axi_port_cfg[name] = AxiIntfConf(name, pconf['type'])
            for subintf in ['araddr', 'rdata', 'awaddr', 'wdata']:
                if subintf not in pconf:
                    continue

                axi_port_cfg[name].comp[subintf] = get_port_def(
                    top, pconf[subintf], name, subintf, axi_port_cfg[name], pconf)

        elif pconf['type'] in ['axis']:
            axi_port_cfg[name] = AxiIntfConf(name, pconf['type'])
            for subintf in ['tdata']:
                if subintf not in pconf:
                    continue

                axi_port_cfg[name].comp[subintf] = get_port_def(
                    top, pconf[subintf], name, subintf, axi_port_cfg[name], pconf)


    for name, p in axi_port_cfg.copy().items():
        if p.t in ['axidma']:
            if 'rdata' in p.comp:
                p.comp['araddr'] = AxiPortConf(p, 'araddr', params={'araddr': 32})

            if 'wdata' in p.comp:
                p.comp['awaddr'] = AxiPortConf(p, 'awaddr', params={'awaddr': 32})

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

            axi_port_cfg[f'{name}_ctrl'] = AxiIntfConf(
                f'{name}_ctrl', 'axilite', axil_comp)

            if 'wdata' in p.comp and 'bresp' not in p.comp:
                p.comp['bresp'] = AxiPortConf(
                    p, 'bresp', params={'bresp': 'awaddr' in p.comp})

        if p.t in ['axi']:
            if 'wdata' in p.comp and 'awaddr' not in p.comp:
                p.comp['awaddr'] = AxiPortConf(p, 'awaddr', params={'awaddr': 3})

            if 'rdata' in p.comp and 'araddr' not in p.comp:
                p.comp['araddr'] = AxiPortConf(p, 'araddr', params={'araddr': 3})

        if p.t in ['axi', 'bram']:
            if 'wdata' in p.comp and 'awaddr' in p.comp:
                wdata_byte_addr_w = bitw(ceil_div(p.comp['wdata'].params['wdata'], 8) - 1)
                p.comp['awaddr'].params['awaddr'] += wdata_byte_addr_w

            if 'rdata' in p.comp and 'araddr' in p.comp:
                rdata_byte_addr_w = bitw(ceil_div(p.comp['rdata'].params['rdata'], 8) - 1)
                p.comp['araddr'].params['araddr'] += rdata_byte_addr_w

            if 'wdata' in p.comp and 'bresp' not in p.comp:
                p.comp['bresp'] = AxiPortConf(
                    p, 'bresp', params={'bresp': 'awaddr' in p.comp})

    return axi_port_cfg
