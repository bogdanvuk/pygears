import unittest
import subprocess
import inspect
import os
import re
import shutil
from functools import partial, wraps

import jinja2
import pytest

from pygears import clear, find, reg
from pygears.sim import sim
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.hdl import register_hdl_paths
from pygears.hdl import hdlgen, synth
from pygears.hdl import yosys

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

    return os.path.join(test_dir, 'result', os.path.relpath(filename, test_dir), function_name)


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


def formal_check(disable=None, asserts=None, assumes=None, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('formal_check_fixt')(pytest.mark.parametrize(
            'formal_check_fixt', [[disable, asserts, assumes, kwds]], indirect=True)(func))

    return decorator


@pytest.fixture
def formal_check_fixt(tmpdir, request):
    skip_ifndef('FORMAL_TEST')
    yield

    outdir = tmpdir
    disable = request.param[0] if request.param[0] is not None else {}
    asserts = request.param[1] if request.param[1] is not None else {}
    assumes = request.param[2] if request.param[2] is not None else []
    reg['vgen/formal/asserts'] = asserts
    reg['vgen/formal/assumes'] = assumes

    root = find('/')
    module = hdlgen(root.child[0], lang='v', outdir=outdir, wrapper=False, **request.param[3])

    yosis_cmds = []
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__)))
    jinja_context = {'name': module.basename, 'outdir': outdir}

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

    for port in module.in_ports:
        jinja_context['live_task'] = True
        find_yosis_cmd(port.basename)

    for port in module.out_ports:
        jinja_context['live_task'] = False
        find_yosis_cmd(port.basename)

    for cmd in yosis_cmds:
        assert os.system(cmd) == 0, f'Yosis failed. Cmd: {cmd}'


def synth_check(expected, tool='yosys', top=None, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('synth_check_fixt')(pytest.mark.parametrize(
            'synth_check_fixt', [[expected, kwds, tool, top]], indirect=True)(func))

    return decorator


@pytest.fixture
def synth_check_fixt(tmpdir, lang, request):
    skip_ifndef('SYNTH_TEST')

    # lang = 'sv'
    util_ref = request.param[0]
    params = request.param[1]
    tool = request.param[2]
    top = request.param[3]

    if tool == 'vivado':
        skip_ifndef('SYNTH_TEST')

    if tool == 'vivado':
        if not shutil.which('vivado'):
            raise unittest.SkipTest(f"Skipping test, vivado not found")

        params['util'] = True
        params['timing'] = True

    elif tool == 'yosys' and lang == 'v':
        if lang != 'v':
            raise unittest.SkipTest(f"Skipping test, unsupported lang for yosys")

        if not shutil.which('yosys'):
            raise unittest.SkipTest(f"Skipping test, yosys not found")

        params['synthcmd'] = 'synth_xilinx'

        # from pygears.hdl.yosys import synth
        # report = synth(tmpdir, top=top, synth_cmd='synth_xilinx', optimize=True)
    else:
        raise unittest.SkipTest(f"Skipping test, not appropriate tool not found")

    yield

    if top is None:
        top = find('/').child[0]

    util = synth(tool, outdir=tmpdir, top=top, lang=lang, **params)

    if tool == 'vivado':
        util = util['util']

    print(util)

    for param, value in util_ref.items():
        if callable(value):
            assert value(util[param])
        else:
            assert util[param] == value


clear = pytest.fixture(autouse=True)(clear)

def hdl_check(expected, **kwds):
    def decorator(func):
        return pytest.mark.usefixtures('hdl_check_fixt')(pytest.mark.parametrize(
            'hdl_check_fixt', [[expected, kwds]], indirect=True)(func))

    return decorator


@pytest.fixture
def hdl_check_fixt(tmpdir, request):
    reg['gear/infer_signal_names'] = True

    yield

    lang = os.path.splitext(request.param[0][0])[1][1:]
    register_hdl_paths(tmpdir)
    hdlgen(lang=lang, outdir=tmpdir, **request.param[1])

    for fn in request.param[0]:
        res_file = os.path.join(tmpdir, fn)
        ref_file = os.path.join(os.path.splitext(request.fspath)[0], request.function.__name__, fn)

        assert sv_files_equal(res_file, ref_file)


def websim_check(func):
    return pytest.mark.usefixtures('websim_check_fixt')(func)


@pytest.fixture
def websim_check_fixt(tmpdir, sim_cls, request):
    reg['debug/trace'] = ['*']
    reg['debug/webviewer'] = True

    yield

    # tmpdir = '/home/bvu/tmp/dut'
    sim(resdir=tmpdir)

    ref_folder = os.path.join(os.path.splitext(request.fspath)[0], request.function.__name__)
    # ref_folder = '/home/bvu/tmp/dut'
    if sim_cls is None:
        ref_file = os.path.join(ref_folder, 'pygears_sim.json')
    else:
        ref_file = os.path.join(ref_folder, 'pygears_cosim.json')

    with open(os.path.join(tmpdir, 'pygears.json'), 'r') as f1:
        with open(ref_file, 'r') as f2:
            assert f1.read() == f2.read()
        # with open(ref_file, 'w') as f2:
        #     return f2.write(f1.read())


def skip_ifndef(*envars):
    import unittest
    import os
    if any(v not in os.environ for v in envars):
        raise unittest.SkipTest(f"Skipping test, {envars} not defined")


def skip_sim_if_no_tools():
    if ('VERILATOR_ROOT' not in os.environ) or ('SYSTEMC_HOME'
                                                not in os.environ) or ('SCV_HOME'
                                                                       not in os.environ):
        raise unittest.SkipTest("Such-and-such failed. Skipping all tests in foo.py")


@pytest.fixture(params=[
    None,
    # partial(SimVerilated, lang='v'),
    partial(SimVerilated, lang='sv'),
    SimSocket,
])
def sim_cls(request):
    sim_cls = request.param
    if sim_cls is SimVerilated:
        skip_ifndef('VERILATOR_ROOT')
    elif sim_cls is SimSocket:
        skip_ifndef('SIM_SOCKET_TEST')
        sim_cls = partial(SimSocket, run=True, sim='xsim')

    yield sim_cls


@pytest.fixture(params=[
    partial(SimVerilated, lang='v'),
    partial(SimVerilated, lang='sv'),
    SimSocket,
])
def cosim_cls(request):
    cosim_cls = request.param
    if cosim_cls is SimVerilated:
        skip_ifndef('VERILATOR_ROOT')
    elif cosim_cls is SimSocket:
        skip_ifndef('SIM_SOCKET_TEST')
        cosim_cls = partial(SimSocket, run=True, sim='xsim')

    yield cosim_cls


@pytest.fixture(params=['v', 'sv'])
def lang(request):
    lang = request.param
    # if lang is 'v':
    #     skip_ifndef('VERILOG_TEST')
    yield lang


from pygears import gear
from pygears.lib import decouple


def get_decoupled_dut(delay, f):
    if delay > 0:
        return f

    @gear
    def decoupled(*din):
        return din | f | decouple

    return decoupled
