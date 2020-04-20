from dataclasses import dataclass
from pygears.typing.math import ceil_chunk, ceil_pow2


@dataclass
class Port:
    name: str
    direction: str
    width: int


AXI_SLAVE = {
    'common': [
        Port('aclk', 'in', 0),
        Port('aresetn', 'in', 0),
    ],
    'waddr': [
        Port('awaddr', 'in', -1),
        Port('awprot', 'in', 3),
        Port('awvalid', 'in', 0),
        Port('awready', 'out', 0),
        Port('awsize', 'in', 3),
        Port('awburst', 'in', 2),
        Port('awcache', 'in', 4),
        Port('awlen', 'in', 8),
    ],
    'waddr_qos': [
        Port('awlock', 'in', 1),
        Port('awqos', 'in', 4),
        Port('awregion', 'in', 4),
    ],
    'wdata': [
        Port('wdata', 'in', -1),
        Port('wstrb', 'in', -1),
        Port('wvalid', 'in', 0),
        Port('wready', 'out', 0),
        Port('wlast', 'in', 0),
    ],
    'bresp': [
        Port('bresp', 'out', 2),
        Port('bvalid', 'out', 0),
        Port('bready', 'in', 0),
    ],
    'raddr': [
        Port('araddr', 'in', -1),
        Port('arid', 'in', 'C_AXI_ID_WIDTH-1'),
        Port('arprot', 'in', 3),
        Port('arvalid', 'in', 0),
        Port('arready', 'out', 0),
        Port('arsize', 'in', 3),
        Port('arburst', 'in', 2),
        Port('arcache', 'in', 4),
        Port('arlen', 'in', 8),
    ],
    'raddr_qos': [
        Port('arlock', 'in', 1),
        Port('arqos', 'in', 4),
        Port('arregion', 'in', 4),
    ],
    'rdata': [
        Port('rdata', 'out', -1),
        Port('rresp', 'out', 2),
        Port('rvalid', 'out', 0),
        Port('rready', 'in', 0),
        Port('rlast', 'out', 0),
    ],
}

AXIL_SLAVE = {
    'common': [
        Port('aclk', 'in', 0),
        Port('aresetn', 'in', 0),
    ],
    'waddr': [
        Port('awaddr', 'in', -1),
        Port('awprot', 'in', 3),
        Port('awvalid', 'in', 0),
        Port('awready', 'out', 0),
    ],
    'wdata': [
        Port('wdata', 'in', -1),
        Port('wstrb', 'in', -1),
        Port('wvalid', 'in', 0),
        Port('wready', 'out', 0),
    ],
    'bresp': [
        Port('bresp', 'out', 2),
        Port('bvalid', 'out', 0),
        Port('bready', 'in', 0),
    ],
    'raddr': [
        Port('araddr', 'in', -1),
        Port('arprot', 'in', 3),
        Port('arvalid', 'in', 0),
        Port('arready', 'out', 0),
    ],
    'rdata': [
        Port('rdata', 'out', -1),
        Port('rresp', 'out', 2),
        Port('rvalid', 'out', 0),
        Port('rready', 'in', 0),
    ],
}

AXIS_SLAVE = {
    'common': [
        Port('aclk', 'in', 0),
        Port('aresetn', 'in', 0),
    ],
    'data': [
        Port('tdata', 'in', -1),
        Port('tvalid', 'in', 0),
        Port('tready', 'out', 0),
    ],
    'last': [
        Port('tlast', 'in', 0),
    ]
}

AXIS_MASTER = {
    'common': [
        Port('aclk', 'in', 0),
        Port('aresetn', 'in', 0),
    ],
    'data': [
        Port('tdata', 'out', -1),
        Port('tvalid', 'out', 0),
        Port('tready', 'in', 0),
    ],
    'last': [
        Port('tlast', 'out', 0),
    ]
}


def subport_def(subintf, prefix, **kwds):
    ret = []
    for p in subintf:
        width = p.width
        if p.width == -1:
            if p.name in kwds:
                width = kwds[p.name]
            elif 'dflt' in kwds:
                width = kwds['dflt']
            else:
                breakpoint()
                raise Exception(f'Port "{p.name}" wasn\'t supplied a parameter')

            if p.name in ['tdata', 'wdata', 'rdata'] and isinstance(width, int):
                width = ceil_chunk(ceil_pow2(int(width)), 32)

        direction = 'input' if p.direction == 'in' else 'output'
        name = f'{prefix}_{p.name}'

        if width == 0:
            ret.append(f'{direction} {name}')
        elif isinstance(width, str):
            ret.append(f'{direction} [{width}:0] {name}')
        else:
            ret.append(f'{direction} [{width-1}:0] {name}')

    return ret


def port_def(intf, prefix, **kwds):
    ret = []
    for subintf in intf:
        if subintf in kwds:
            subkwds = {}
            if isinstance(kwds[subintf], dict):
                subkwds = kwds[subintf]
            elif isinstance(kwds[subintf], bool):
                if not kwds[subintf]:
                    continue
            elif isinstance(kwds[subintf], int):
                subkwds = {'dflt': kwds[subintf]}

            ret.extend(subport_def(intf[subintf], prefix, **subkwds))

    return ret


def port_map(intf, prefix_src, prefix_dest, uppercase=False, **kwds):
    ret = []
    for subintf in intf:
        if not kwds.get(subintf, False):
            continue

        for p in intf[subintf]:
            dest = f'{prefix_dest}_{p.name}'

            if uppercase:
                dest = dest.upper()

            ret.append(f'.{dest}({prefix_src}_{p.name})')

    return ret
