# import os
# import inspect
# import runpy
# import argparse
# from pygears import config
# from pygears.entry import EntryPlugin
# from pygears.conf.custom_settings import load_rc
# from .yosys import synth as yosys_synth


# def synth_entry(args):
#     if args.design is None:
#         args.design = inspect.stack()[0][1]

#     runpy.run_path(args.design)

#     kwds = vars(args)
#     del kwds['func']
#     synth(**kwds)


# def synth(tool, design=None, top=None, **kwds):
#     if tool not in config['synth/backend']:
#         raise Exception(f'Unknown backend synth tool "{tool}".')

#     design = os.path.abspath(os.path.expanduser(design))

#     load_rc('.pygears', os.path.dirname(design))

#     config['synth/backend'][tool](top, design=design, **kwds)


# class SynthPlugin(EntryPlugin):
#     @classmethod
#     def bind(cls):
#         subparsers = config['entry/subparsers']
#         synth = subparsers.add_parser('synth', aliases=['ip'])
#         synth.set_defaults(func=synth_entry)

#         parent_parser = argparse.ArgumentParser(add_help=False)
#         parent_parser.add_argument('-I',
#                                    '--include',
#                                    action='append',
#                                    default=[],
#                                    help="HDL include directory")
#         parent_parser.add_argument('--design', '-d', type=str)
#         parent_parser.add_argument('--top', '-t', type=str, default='/')
#         parent_parser.add_argument('--build', '-b', action='store_true')
#         parent_parser.add_argument('--outdir', '-o', type=str)
#         parent_parser.add_argument('--lang',
#                                    '-l',
#                                    type=str,
#                                    choices=['v', 'sv'],
#                                    default='sv')
#         parent_parser.add_argument('--copy', '-c', action='store_true')
#         parent_parser.add_argument('--makefile', '-m', action='store_true')

#         subsynth = synth.add_subparsers(title='actions', dest='tool')

#         config.define('synth/backend', default={'yosys': yosys_synth})
#         config.define('synth/subparser', default=subsynth)
#         config.define('synth/baseparser', default=parent_parser)
