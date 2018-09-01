import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_SVLIB_DIR = os.path.join(ROOT_DIR, 'common', 'svlib')
COOKBOOK_SVLIB_DIR = os.path.join(ROOT_DIR, 'cookbook', 'svlib')
USER_SVLIB_DIR = os.path.expanduser('~/.pygears/svlib')
