import os
import jinja2
from .axi import get_axi_conf
from pygears import registry, find
from pygears.typing import Queue, typeof
from pygears.core.gear import InSig
from pygears.hdl import hdlgen
from pygears.hdl.templenv import get_port_intfs
from pygears.hdl.templenv import TemplateEnv
from pygears.typing.math import ceil_chunk, ceil_div, ceil_pow2
from pygears.util.fileio import save_file
from . import axi_intfs


def generate(top, intf):
    if isinstance(top, str):
        top = find(top)

    axi_port_cfg = get_axi_conf(top, intf)

    modinst = registry('svgen/map')[top]

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
            w_data = int(dtype.data)
            w_eot = int(dtype.eot)

        i['w_data'] = w_data
        i['w_eot'] = w_eot

    defs = []
    for name, p in axi_port_cfg.items():
        if p['type'] == 'axidma':
            wdata = False
            if 'wdata' in p:
                wdata = {'wdata': p['wdata'], 'wstrb': p['wdata']//8}

            pdefs = axi_intfs.port_def(
                axi_intfs.AXI_SLAVE,
                name,
                raddr=p.get('raddr', {}).get('width', 32),
                rdata=p.get('rdata', {}).get('width', False))

            defs.extend(pdefs)

            pdefs = axi_intfs.port_def(
                axi_intfs.AXIL_SLAVE,
                name,
                waddr=5,
                wdata={'wdata': 32, 'wstrb': 4},
                raddr=5,
                rdata=32)

            defs.extend(pdefs)

        elif p['type'] in ['bram', 'bram.req', 'axi']:

            wdata = False
            if 'wdata' in p:
                wdata = {'wdata': p['wdata']['width'], 'wstrb': p['wdata']['width']//8}

            pdefs = axi_intfs.port_def(
                axi_intfs.AXI_SLAVE,
                name,
                waddr=p.get('waddr', {}).get('width', False),
                wdata=wdata,
                bresp=('waddr' in p),
                raddr=p.get('raddr', {}).get('width', False),
                rdata=p.get('rdata', {}).get('width', False))

            defs.extend(pdefs)

        elif p['type'] == 'axis':
            if p['direction'] == 'in':
                tmplt = axi_intfs.AXIS_SLAVE
            else:
                tmplt = axi_intfs.AXIS_MASTER

            pdefs = axi_intfs.port_def(tmplt, name, data=p['width'], last=p['w_eot'] > 0)

            defs.extend(pdefs)

    print(axi_port_cfg)
    print(defs)
    context = {
        'wrap_module_name': f'wrap_{modinst.module_name}',
        'module_name': modinst.module_name,
        'inst_name': modinst.inst_name,
        'intfs': intfs,
        'sigs': sigs,
        'param_map': modinst.params,
        'port_def': defs,
        'ports': axi_port_cfg
    }

    context['pg_clk'] = 'aclk'
    tmplt = 'wrapper.j2'

    base_addr = os.path.dirname(__file__)
    print(os.path.join(os.path.dirname(base_addr), 'sv'))
    lang_dir = os.path.join(os.path.dirname(base_addr), 'sv')
    env = TemplateEnv(lang_dir)

    # env = jinja2.Environment(
    #     extensions=['jinja2.ext.do'],
    #     loader=jinja2.FileSystemLoader([base_addr, os.path.join(os.path.dirname(base_addr), 'sv')]),
    #     trim_blocks=True,
    #     lstrip_blocks=True)

    env.jenv.globals.update(
        zip=zip,
        ceil_pow2=ceil_pow2,
        ceil_div=ceil_div,
        ceil_chunk=ceil_chunk,
        axi_intfs=axi_intfs)

    wrp = env.render(base_addr, tmplt, context)

    # env.globals.update(
    #     zip=zip,
    #     ceil_pow2=ceil_pow2,
    #     ceil_div=ceil_div,
    #     ceil_chunk=ceil_chunk,
    #     axi_intfs=axi_intfs)

    # wrp = env.get_template(tmplt).render(context)
    return wrp
    # save_file(f'wrap_{os.path.basename(modinst.file_basename)}', dirs['hdl'], wrp)
