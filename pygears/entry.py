import sys
import os
import inspect
import runpy
import argparse

from pygears import PluginBase, __version__, reg
from pygears.conf import inject, Inject
from pygears.conf.custom_settings import load_rc


@inject
def main(argv=sys.argv, config=Inject('entry')):

    args = config['parser'].parse_args(argv[1:])

    cmd = args.command


    kwds = vars(args)
    print(kwds)

    del kwds['command']

    func = config['cmds'][cmd]['entry']

    func(**kwds)


@inject
def cmd_register(
    path,
    cmd_entry,
    aliases=(),
    structural=False,
    tree=Inject('entry'),
    derived=False,
    help=None,
    dest=None):

    for i, p in enumerate(path[:-1]):
        cmds = tree['cmds']
        if p not in cmds:
            raise Exception(f'Parent command does not exist: {"/".join(path[:i])}')

        tree = tree['cmds'][p]

    name = path[-1]
    cmd_config = tree['cmds'].subreg(name)

    parents = []
    if derived:
        parents = [tree['baseparser']]

    cmd_config['parser'] = tree['subparsers'].add_parser(
        name, aliases=aliases, parents=parents, help=help)

    if structural:
        cmd_config['subparsers'] = cmd_config['parser'].add_subparsers(
            title='subcommands',
            help='subcommand help',
            dest=dest)

        import sys
        if sys.version_info[1] >= 7:
            cmd_config['subparsers'].required = cmd_entry is None

    cmd_config['baseparser'] = argparse.ArgumentParser(add_help=False)

    cmd_config.subreg('cmds')
    cmd_config['entry'] = cmd_entry

    return cmd_config


def entry(path, aliases=None):
    def wrapper(f):
        cmd_register(path, cmd_entry=f, aliases=aliases)

    return wrapper


def design_exec_entry(f):
    def cmd_entry(**kwds):
        if kwds['design'] is None:
            kwds['design'] = inspect.stack()[0][1]
        else:
            runpy.run_path(kwds['design'])

        kwds['design'] = os.path.abspath(os.path.expanduser(kwds['design']))

        load_rc('.pygears', os.path.dirname(kwds['design']))

        f(**kwds)

    return f


class EntryPlugin(PluginBase):
    @classmethod
    def bind(cls):
        parser = argparse.ArgumentParser(
            description='Hardware Design: A Functional Approach')
        parser.add_argument(
            '--version', action='version', version=f'pygears {__version__}')

        subparsers = parser.add_subparsers(title='subcommands', help='subcommand help', dest='command')

        reg.subreg('entry', {'parser': parser, 'subparsers': subparsers})
        reg['entry'].subreg('cmds')
