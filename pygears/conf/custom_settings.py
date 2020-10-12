import inspect
import sys
import json
import os
import pprint
import runpy

from .log import conf_log
from .registry import PluginBase, reg
from .utils import dict_generator


def print_registry():
    # monkey patch sorting
    pprint._safe_key.__lt__ = lambda x, y: True

    preg = pprint.pformat(reg)
    conf_log().info(f'Registry settings:\n{preg}')


def load_rc_from_dir(rc_fn, dirname):
    rc_path = os.path.join(dirname, f'{rc_fn}.py')
    if os.path.exists(rc_path):
        runpy.run_path(rc_path)
        return

    conf = None
    rc_path = os.path.join(dirname, f'{rc_fn}.yaml')
    if os.path.exists(rc_path):
        with open(rc_path) as f:
            try:
                import yaml
                conf = yaml.safe_load(f)
            except ImportError:
                conf_log().warning(
                    f'PyGears YAML configuration file found'
                    f'at "{rc_path}", but yaml python package not '
                    f'installed')

    rc_path = os.path.join(dirname, f'{rc_fn}.json')
    if os.path.exists(rc_path):
        with open(rc_path) as f:
            conf = json.load(f)

    if conf:
        for c_list in dict_generator(conf):
            keys = '/'.join([str(x) for x in c_list[:-1]])
            reg[keys] = c_list[-1]


def load_rc(rc_fn, dirname=None):
    search_dirs = []

    if dirname is None:
        if hasattr(sys.modules['__main__'], '__file__'):
            dirname = os.path.dirname(sys.modules['__main__'].__file__)
        else:
            dirname = os.getcwd()

    while dirname != os.path.abspath(os.sep):
        search_dirs.append(dirname)
        dirname = os.path.abspath(os.path.join(dirname, '..'))

    home_path = os.path.expanduser("~")
    if home_path not in search_dirs:
        search_dirs.append(home_path)

    pg_home = os.path.join(home_path, '.pygears')
    if pg_home not in search_dirs:
        search_dirs.append(pg_home)

    unique_search_dirs = list(dict.fromkeys(search_dirs))
    for path in reversed(unique_search_dirs):
        load_rc_from_dir(rc_fn, path)
