from pygears import PluginBase, config, __version__
from pygears.conf import inject, Inject

import argparse
import sys


@inject
def main(argv=sys.argv, parser=Inject('entry/parser')):
    args = parser.parse_args(argv[1:])
    args.func(args)


class EntryPlugin(PluginBase):
    @classmethod
    def bind(cls):
        parser = argparse.ArgumentParser(
            description='Hardware design: functional approach')
        parser.add_argument('--version',
                            action='version',
                            version=f'pygears {__version__}')

        subparsers = parser.add_subparsers()
        config.define('entry/parser', default=parser)
        config.define('entry/subparsers', default=subparsers)
