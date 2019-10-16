import os
import inspect
import runpy
import argparse
from pygears import config
from pygears.entry import EntryPlugin
from pygears.hdl import find_rtl_top


def ipgen_entry(args):
    if args.design is None:
        args.design = inspect.stack()[0][1]

    runpy.run_path(args.design)

    ipgen(
        tool=args.tool,
        top=args.top,
        design=args.design,
        outdir=args.outdir,
        include=args.include,
        lang=args.lang,
        build=args.build,
        copy=args.copy,
        makefile=args.makefile,
    )


def ipgen(
        tool,
        top=None,
        design=None,
        outdir=None,
        include=[],
        lang='sv',
        build=False,
        copy=True,
        makefile=False,
):
    design = os.path.abspath(os.path.expanduser(design))

    config['ipgen/backend'][tool](top,
                                  design=design,
                                  outdir=outdir,
                                  include=include,
                                  lang=lang,
                                  build=build,
                                  copy=copy,
                                  makefile=makefile)


class IpgenPlugin(EntryPlugin):
    @classmethod
    def bind(cls):
        subparsers = config['entry/subparsers']
        ipgen = subparsers.add_parser('ipgen', aliases=['ip'])
        ipgen.set_defaults(func=ipgen_entry)

        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument('-I',
                                   '--include',
                                   action='append',
                                   default=[],
                                   help="HDL include directory")
        parent_parser.add_argument('--design', '-d', type=str)
        parent_parser.add_argument('--top', '-t', type=str, default='/')
        parent_parser.add_argument('--build', '-b', action='store_true')
        parent_parser.add_argument('--outdir', '-o', type=str)
        parent_parser.add_argument('--lang',
                                   '-l',
                                   type=str,
                                   choices=['v', 'sv'],
                                   default='sv')
        parent_parser.add_argument('--copy', '-c', action='store_true')
        parent_parser.add_argument('--makefile', '-m', action='store_true')

        subipgen = ipgen.add_subparsers(title='actions', dest='tool')

        config.define('ipgen/backend', default={})
        config.define('ipgen/subparser', default=subipgen)
        config.define('ipgen/baseparser', default=parent_parser)
