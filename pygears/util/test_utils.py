import pytest
import jinja2
import re
import os
import inspect
import shutil

from pygears.svgen import svgen, register_sv_paths
from pygears.sim import sim
from pygears import registry, clear
from functools import wraps
from pygears.definitions import COMMON_SVLIB_DIR

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

    print(os.getcwd())
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


def synth_check(expected, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('synth_check_fixt')(
            pytest.mark.parametrize(
                'synth_check_fixt', [[expected, kwds]], indirect=True)(func))

    return decorator


@pytest.fixture
def synth_check_fixt(tmpdir, request):
    skip_ifndef('SYNTH_TEST')
    yield

    outdir = tmpdir
    register_sv_paths(outdir)
    svgen(outdir=outdir, **request.param[1])

    files = []
    for svmod in registry("svgen/map").values():
        if not hasattr(svmod, 'sv_module_path'):
            continue

        path = svmod.sv_module_path
        if not path:
            path = os.path.join(outdir, svmod.sv_file_name)

        files.append(path)

    files.append(os.path.join(COMMON_SVLIB_DIR, 'dti.sv'))

    viv_cmd = (
        f'vivado -mode batch -source {outdir}/synth.tcl -nolog -nojournal')

    jinja_context = {'res_dir': os.path.join(outdir, 'vivado'), 'files': files}

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__)))

    env.get_template('synth.j2').stream(jinja_context).dump(
        f'{outdir}/synth.tcl')

    def row_data(line):
        return [row.strip().lower() for row in line.split('|') if row.strip()]

    assert os.system(viv_cmd) == 0, "Vivado build failed"
    with open(f'{outdir}/vivado/utilization.txt') as f:
        tbl_section = 0
        for line in f:
            if line[0] == '+':
                tbl_section += 1
            elif tbl_section == 1:
                header = row_data(line)[2:]
            elif tbl_section == 2:
                values = [float(v) for v in row_data(line)[2:]]
                break

        util = dict(zip(header, values))

    for param, value in request.param[0].items():
        assert util[param] == value


def svgen_check(expected, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('svgen_check_fixt')(
            pytest.mark.parametrize(
                'svgen_check_fixt', [[expected, kwds]], indirect=True)(func))

    return decorator


clear = pytest.fixture(autouse=True)(clear)


@pytest.fixture
def svgen_check_fixt(tmpdir, request):
    yield

    register_sv_paths(tmpdir)
    svgen(outdir=tmpdir, **request.param[1])

    for fn in request.param[0]:
        res_file = os.path.join(tmpdir, fn)
        ref_file = os.path.join(
            os.path.splitext(request.fspath)[0], request.function.__name__, fn)

        assert sv_files_equal(res_file, ref_file)


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
        raise unittest.SkipTest(f"Skipping test, {envars} not defined")


def skip_sim_if_no_tools():
    import unittest
    import os
    if ('VERILATOR_ROOT' not in os.environ) or (
            'SYSTEMC_HOME' not in os.environ) or (
                'SCV_HOME' not in os.environ):
        raise unittest.SkipTest(
            "Such-and-such failed. Skipping all tests in foo.py")
