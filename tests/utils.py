import re
import os
import inspect
import shutil

from pygears.svgen import svgen
from functools import wraps

re_trailing_space_rem = re.compile(r"\s+$", re.MULTILINE)
re_multispace_rem = re.compile(r"^\s+", re.MULTILINE)
re_multi_comment_rem = re.compile(r"/\*.*?\*/", re.DOTALL)
re_comment_rem = re.compile(r"//.*$", re.MULTILINE)

rem_pipe = [
    re_multi_comment_rem, re_comment_rem, re_multispace_rem,
    re_trailing_space_rem
]


def remove_unecessary(s):

    for r in rem_pipe:
        s = r.sub('', s)

    return s.strip()


def equal_on_nonspace(str1, str2):
    # print(remove_unecessary(str1))
    # print('-----------------------')
    # print(remove_unecessary(str2))
    # print('-----------------------')
    return remove_unecessary(str1) == remove_unecessary(str2)


def sv_files_equal(fn1, fn2):
    with open(fn1, 'r') as f1:
        with open(fn2, 'r') as f2:
            return equal_on_nonspace(f1.read(), f2.read())


def get_cur_test_name():
    for _, filename, _, function_name, _, _ in inspect.stack():
        if function_name.startswith('test_'):
            return os.path.splitext(filename)[0], function_name
    else:
        raise Exception("Has to be run from within a test function")


def get_result_dir(filename=None, function_name=None):
    if not filename:
        filename, function_name = get_cur_test_name()

    return os.path.join(
        os.path.dirname(__file__), 'result',
        filename, function_name)


def prepare_result_dir(filename=None, function_name=None):
    res_dir = get_result_dir(filename, function_name)
    try:
        shutil.rmtree(res_dir)
    except FileNotFoundError:
        pass

    os.makedirs(res_dir, exist_ok=True)

    return res_dir


def sv_file_equal_to_ref(fn, filename=None, function_name=None):
    if not filename:
        filename, function_name = get_cur_test_name()

    res_dir = get_result_dir(filename, function_name)

    return sv_files_equal(
        os.path.join(function_name, fn), os.path.join(res_dir, fn))


def svgen_test(files):
    def decorator(func):
        @wraps(func)
        def wrapper():
            func()
            filename = os.path.splitext(inspect.getfile(func))[0]

            outdir = prepare_result_dir(filename, func.__name__)
            svgen(outdir=outdir)

            for fn in files:
                assert sv_file_equal_to_ref(fn, filename, func.__name__)

        return wrapper

    return decorator
