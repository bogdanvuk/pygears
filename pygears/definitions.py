import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

LIB_SVLIB_DIR = os.path.join(ROOT_DIR, 'lib', 'svlib')
USER_SVLIB_DIR = os.path.expanduser('~/.pygears/svlib')

LIB_VLIB_DIR = os.path.join(ROOT_DIR, 'lib', 'vlib')
USER_VLIB_DIR = os.path.expanduser('~/.pygears/vlib')

CACHE_DIR = os.path.join(
    os.environ.get('XDG_CACHE_HOME',
                   os.path.join(os.path.expandvars("$HOME"), '.cache')),
    'pygears')
