import re
import os
import inspect
import shutil

from pygears.svgen import svgen
from pygears.sim import sim
from functools import wraps

re_trailing_space_rem = re.compile(r"\s+$", re.MULTILINE)
re_multispace_rem = re.compile(r"\s+", re.MULTILINE)
re_multi_comment_rem = re.compile(r"/\*.*?\*/", re.DOTALL)
re_comment_rem = re.compile(r"//.*$", re.MULTILINE)

rem_pipe = {
    re_multi_comment_rem: '',
    re_comment_rem: '',
    re_multispace_rem: ' ',
    re_trailing_space_rem: ''
}


def remove_unecessary(s):

    for r, repl in rem_pipe.items():
        s = r.sub(repl, s)

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

    test_dir = os.path.dirname(__file__)

    return os.path.join(test_dir, 'result', os.path.relpath(
        filename, test_dir), function_name)


def prepare_result_dir(filename=None, function_name=None):
    res_dir = get_result_dir(filename, function_name)
    try:
        shutil.rmtree(res_dir)
    except FileNotFoundError:
        pass

    os.makedirs(res_dir, exist_ok=True)

    return res_dir


def get_sv_file_comparison_pair(fn, filename=None, function_name=None):
    if not filename:
        filename, function_name = get_cur_test_name()

    res_dir = get_result_dir(filename, function_name)
    return os.path.join(filename, function_name, fn), os.path.join(res_dir, fn)


def get_test_res_ref_dir_pair(func):
    filename = os.path.splitext(os.path.abspath(inspect.getfile(func)))[0]

    outdir = prepare_result_dir(filename, func.__name__)

    return filename, outdir


def svgen_check(files, **kwds):
    def decorator(func):
        @wraps(func)
        def wrapper():
            func()
            filename, outdir = get_test_res_ref_dir_pair(func)
            svgen(outdir=outdir, **kwds)

            for fn in files:
                comp_file_paths = get_sv_file_comparison_pair(
                    fn, filename, func.__name__)

                assert sv_files_equal(
                    *comp_file_paths
                ), f'{comp_file_paths[0]} != {comp_file_paths[1]}'

        return wrapper

    return decorator


def sim_check(**kwds):
    def decorator(func):
        @wraps(func)
        def wrapper():
            report = func()
            filename, outdir = get_test_res_ref_dir_pair(func)
            sim(outdir=outdir, **kwds)

            assert all(item['match'] for item in report)

        return wrapper

    return decorator


def skip_ifndef(*envars):
    import unittest
    import os
    if any(v not in os.environ for v in envars):
        raise unittest.SkipTest(
            f"Skipping test, {envars} not defined")


def skip_sim_if_no_tools():
    import unittest
    import os
    if ('VERILATOR_ROOT' not in os.environ) or (
            'SYSTEMC_HOME' not in os.environ) or (
                'SCV_HOME' not in os.environ):
        raise unittest.SkipTest(
            "Such-and-such failed. Skipping all tests in foo.py")
