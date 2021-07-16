import os
import jinja2
from .axi import get_axi_conf
from pygears import reg, find
from pygears.typing import Queue, typeof
from pygears.core.gear import InSig
from pygears.hdl import hdlgen
from pygears.hdl.templenv import get_port_intfs
from pygears.hdl.templenv import TemplateEnv
from pygears.typing.math import ceil_chunk, ceil_div, ceil_pow2, bitw
from pygears.util.fileio import save_file
from . import axi_intfs


def generate(top, intfdef, rst=True):
    files = set()
    if isinstance(top, str):
        top = find(top)

    modinst = reg['hdlgen/map'][top]

    sigs = []
    for s in top.signals.values():
        if s.name == 'clk':
            sigs.append(InSig('aclk', 1))
        elif s.name == 'rst':
            sigs.append(InSig('aresetn', 1))
        else:
            sigs.append(s)

    intfs = {p['name']: p for p in get_port_intfs(top)}

    for i in intfs.values():
        dtype = i['type']
        w_data = i['width']
        w_eot = 0
        if typeof(dtype, Queue):
            w_data = dtype.data.width
            w_eot = dtype.eot.width

        i['w_data'] = w_data
        i['w_eot'] = w_eot

    defs = []
    for name, p in intfdef.items():
        if p.t == 'axidma':
            params = {n: c.params for n, c in p.comp.items()}
            defs.extend(axi_intfs.port_def(axi_intfs.AXI_MASTER, name, **params))

            params = {n: c.params for n, c in intfdef[f'{name}_ctrl'].comp.items()}
            defs.extend(axi_intfs.port_def(axi_intfs.AXIL_SLAVE, f'{name}_ctrl', **params))

            files.update({'sfifo.v', 'axi_addr.v', 'skidbuffer.v'})

            if 'rdata' in p.comp:
                files.add('aximm2s.v')

            if 'wdata' in p.comp:
                files.add('axis2mm.v')

        elif p.t in ['bram', 'bram.req', 'axi']:

            params = {n: c.params for n, c in p.comp.items()}

            pdefs = axi_intfs.port_def(axi_intfs.AXI_SLAVE, name, **params)

            if 'rdata' in params:
                files.add('axi_slave_read.v')

            if 'wdata' in params:
                files.add('axi_slave_write.v')

            if 'rdata' in params or 'wdata' in params:
                files.update({'sfifo.v', 'axi_addr.v', 'skidbuffer.v'})

            defs.extend(pdefs)

        elif p.t == 'axis':
            if p.direction == 'w':
                tmplt = axi_intfs.AXIS_SLAVE
            else:
                tmplt = axi_intfs.AXIS_MASTER

            params = {n: c.params for n, c in p.comp.items()}

            pdefs = axi_intfs.port_def(tmplt, name, **params)

            defs.extend(pdefs)

    context = {
        'wrap_module_name': f'wrap_{modinst.module_name}',
        'module_name': modinst.wrap_module_name,
        'inst_name': modinst.wrap_module_name,
        'intfs': intfs,
        'sigs': sigs,
        'rst': rst,
        'param_map': modinst.params if not modinst.wrapped else {},
        'port_def': defs,
        'ports': intfdef
    }

    context['pg_clk'] = 'aclk'
    tmplt = 'wrapper.j2'

    base_addr = os.path.dirname(__file__)
    lang_dir = os.path.join(os.path.dirname(base_addr), 'sv')
    env = TemplateEnv(lang_dir)

    env.jenv.globals.update(
        zip=zip,
        ceil_pow2=ceil_pow2,
        ceil_div=ceil_div,
        bitw=bitw,
        ceil_chunk=ceil_chunk,
        axi_intfs=axi_intfs)

    return env.render(base_addr, tmplt, context), files
