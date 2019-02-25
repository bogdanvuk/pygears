import pytest
import jinja2
import re
import os
import inspect
import shutil

from pygears.svgen import svgen, register_sv_paths
from pygears.vgen import vgen
from pygears.sim import sim
from pygears import registry, clear
from functools import wraps
from itertools import islice
from pygears.definitions import COMMON_SVLIB_DIR
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated

from functools import partial
from pygears.util.find import find

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


def formal_check(disable=None, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('formal_check_fixt')(
            pytest.mark.parametrize(
                'formal_check_fixt', [[disable, kwds]], indirect=True)(func))

    return decorator


@pytest.fixture
def formal_check_fixt(tmpdir, request):
    skip_ifndef('FORMAL_TEST')
    yield

    outdir = tmpdir

    vgen(outdir=outdir, wrapper=False, assertions=True, **request.param[1])

    # TODO : hack to find gear
    for svmod in registry("svgen/map").values():
        if hasattr(svmod, 'is_compiled') and svmod.is_compiled:
            gear = svmod.node.gear

    disable = request.param[0] if request.param[0] is not None else {}
    yosis_cmds = []
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__)))
    jinja_context = {'name': gear.basename, 'outdir': outdir}

    def find_yosis_cmd(name):
        if name in disable:
            if disable[name] == 'all':
                return
            if disable[name] == 'live':
                jinja_context['live_task'] = False
        script_path = f'{outdir}/top_{name}.sby'
        jinja_context['if_name'] = name.upper()
        env.get_template('formal.j2').stream(jinja_context).dump(script_path)
        yosis_cmds.append(f'sby {script_path}')

    for port in gear.in_ports:
        jinja_context['live_task'] = True
        find_yosis_cmd(port.basename)

    for port in gear.out_ports:
        jinja_context['live_task'] = False
        find_yosis_cmd(port.basename)

    for cmd in yosis_cmds:
        assert os.system(cmd) == 0, f'Yosis failed. Cmd: {cmd}'


def synth_check(expected, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('synth_check_fixt')(
            pytest.mark.parametrize(
                'synth_check_fixt', [[expected, kwds]], indirect=True)(func))

    return decorator


@pytest.fixture
def synth_check_fixt(tmpdir, language, request):
    skip_ifndef('SYNTH_TEST')
    yield

    outdir = tmpdir
    if language == 'sv':
        svgen(outdir=outdir, wrapper=True, **request.param[1])

        files = []
        for svmod in registry("svgen/map").values():
            if not hasattr(svmod, 'sv_impl_path'):
                continue

            path = svmod.sv_impl_path
            if not path:
                path = os.path.join(outdir, svmod.sv_file_name)

            files.append(path)

        files.append(os.path.join(COMMON_SVLIB_DIR, 'dti.sv'))
        files.append(os.path.join(outdir, 'wrap_top.sv'))

    elif language == 'v':
        vgen(outdir=outdir, wrapper=False, **request.param[1])

        files = []
        for svmod in registry("svgen/map").values():
            # TODO : vgen only supports compiled modules for now..
            if hasattr(svmod, 'is_compiled') and svmod.is_compiled:
                path = svmod.sv_impl_path
                if not path:
                    path = os.path.join(outdir, svmod.sv_file_name)

                files.append(path)
    else:
        raise Exception(f"Synth test unknown language: {language}")

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

    with open(f'{outdir}/vivado/timing.txt') as f:
        line = next(islice(f, 2, None))
        util['path delay'] = float(line.split()[1])

    for param, value in request.param[0].items():
        if callable(value):
            assert value(util[param])
        else:
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


@pytest.fixture(params=[None, SimVerilated, SimSocket])
def sim_cls(request):
    sim_cls = request.param
    if sim_cls is SimVerilated:
        skip_ifndef('VERILATOR_ROOT')
    elif sim_cls is SimSocket:
        skip_ifndef('SIM_SOCKET_TEST')
        sim_cls = partial(SimSocket, run=True)

    yield sim_cls


@pytest.fixture(params=[SimVerilated, SimSocket])
def cosim_cls(request):
    cosim_cls = request.param
    if cosim_cls is SimVerilated:
        skip_ifndef('VERILATOR_ROOT')
    elif cosim_cls is SimSocket:
        skip_ifndef('SIM_SOCKET_TEST')
        cosim_cls = partial(SimSocket, run=True)

    yield cosim_cls


@pytest.fixture(params=['sv', 'v'])
def language(request):
    language = request.param
    if language is 'v':
        skip_ifndef('VERILOG_TEST')
    yield language
