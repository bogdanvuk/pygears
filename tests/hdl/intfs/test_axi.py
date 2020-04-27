import os
from pygears import Intf, find
from pygears.lib import sdp, rom, shred, add
from pygears.typing import Tuple, Uint
from pygears.hdl import hdlgen
from pygears.util.fileio import save_file
from pygears.hdl.ipgen import ipgen

from pygears.hdl.intfs.generate import generate

ret = rom(Intf(Uint[8]), data=[], dtype=Uint[24], dflt=0xbbccdd)
top = find('/rom')
outdir = '/tools/home/tmp/axi_test/ip/rom'

# ipgen(
#     'vivado',
#     __file__,
#     outdir=outdir,
#     top='/rom',
#     lang='sv',
#     prjdir='/tools/home/tmp/axi_test/ipprj',
#     intf={'s_axi': {
#         'type': 'axi',
#         'raddr': 'addr',
#         'rdata': 'dout'
#     }})

ret = sdp(Intf(Tuple[Uint[8], Uint[32]]), Intf(Uint[8]))

top = find('/sdp')
outdir = '/tools/home/tmp/axi_test/ip/sdp'

ipgen(
    'vivado',
    __file__,
    outdir=outdir,
    top='/sdp',
    lang='sv',
    prjdir='/tools/home/tmp/axi_test/ipprj',
    intf={'s_axi': {
        'type': 'axi',
        'araddr': 'rd_addr',
        'rdata': 'rd_data',
        'awaddr': 'wr_addr_data',
        'wdata': 'wr_addr_data'
    }})

# ret = shred(Intf(Uint[128]))

# top = find('/shred')
# outdir = '/tools/home/tmp/axi_test/ip/shred'

# ipgen(
#     'vivado',
#     __file__,
#     outdir=outdir,
#     top='/shred',
#     lang='sv',
#     prjdir='/tools/home/tmp/axi_test/ipprj',
#     intf={'din': {
#         'type': 'axidma',
#         'rdata': 'din'
#     }})

# ret = add(Intf(Tuple[Uint[16], Uint[16]]))
# top = find('/add')
# outdir = '/tools/home/tmp/axi_test/ip/add'

# ipgen(
#     'vivado',
#     __file__,
#     outdir=outdir,
#     top='/add',
#     lang='sv',
#     prjdir='/tools/home/tmp/axi_test/ipprj',
#     intf={
#         'din': {
#             'type': 'axi',
#             'wdata': 'din'
#         },
#         'dout': {
#             'type': 'axi',
#             'rdata': 'dout'
#         }
#     })

# {'din': 'axi', 'dout': 'axi'}
