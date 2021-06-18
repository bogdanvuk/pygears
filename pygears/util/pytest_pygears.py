import pytest
import pathlib
from functools import partial
import os


@pytest.hookimpl(hookwrapper=True)
def pytest_exception_interact(node, call, report):
    if not node.config.getoption('--pg'):
        yield
        return

    from pygears import reg
    from pygears.conf import TraceLevel
    if reg['trace/level'] == TraceLevel.debug:
        yield
        return

    import re
    ignore = reg['trace/ignore']
    r = re.compile('  File "(?P<fn>[^"]+)"')

    if hasattr(report.longrepr, 'reprtraceback'):
        for reprs in report.longrepr.reprtraceback.reprentries:
            lines = []
            for l in report.longrepr.reprtraceback.reprentries[0].lines:
                res = r.match(l)
                if res is not None:
                    fn = res.groupdict()['fn']
                    is_internal = any(fn.startswith(d) for d in ignore)
                    is_decorator_gen = '<decorator-gen' in fn
                    if is_internal or is_decorator_gen:
                        continue

                lines.append(l)

            reprs.lines = lines

    yield


@pytest.fixture(autouse=True)
def resdir(tmp_path_factory, pytestconfig):
    if not pytestconfig.getoption('--pg'):
        return None

    from pygears import clear, reg
    from pygears.conf.custom_settings import load_rc
    clear()
    load_rc('.pygears', pytestconfig.rootdir)

    resdir = pytestconfig.getoption("--pg-resdir")

    if resdir is None:
        resdir = str(tmp_path_factory.getbasetemp())

    from pygears import reg
    reg['results-dir'] = resdir

    return resdir


def hook_after(top, args, kwds, file_lock):
    file_lock.release()
    return False


def hook_before(top, args, kwds, config):
    import filelock
    from pygears import reg
    from pygears.sim import cosim_build_dir

    inst_id = cosim_build_dir(top)
    kwds['rebuild'] = False

    kwds['outdir'] = pathlib.Path(kwds['outdir'])
    if config.getoption('--pg-resdir') is None:
        # Xdist creates an extra level of folders. We want one compilation per
        # test run, so we need to go to the parent
        if 'PYTEST_XDIST_WORKER_COUNT' in os.environ:
            kwds['outdir'] = kwds['outdir'].parent

        kwds['outdir'] = kwds['outdir'] / 'sim'

    os.makedirs(kwds['outdir'], exist_ok=True)

    lock_fn = kwds['outdir'] / f'{inst_id}.lock'
    try:
        fl = filelock.FileLock(lock_fn, timeout=0)
        fl.acquire()
        reg['sim/hook/cosim_build_after'].append(partial(hook_after, file_lock=fl))
    except filelock.Timeout:
        with filelock.FileLock(lock_fn):
            pass

    return True


def pytest_runtest_call(item):
    if item.config.getoption('--pg'):
        from pygears import reg
        if item.config.getoption('--pg-reuse'):
            reg['sim/hook/cosim_build_before'].append(partial(hook_before, config=item.config))

    if item.config.getoption('--gearbox'):
        from gearbox.main import main_loop
        main_loop(str(pathlib.Path(item.module.__file__).parent), [], item.runtest, {})
        pytest.skip()


# If any of --pg switches is active, than --pg should be there too
def pytest_load_initial_conftests(args):
    if (any(a.startswith('--pg') for a in args) and not any(a == '--pg' for a in args)):
        args[:] = ['--pg'] + args

    if (not any(a.startswith('--tb') for a in args)):
        args[:] = ['--tb=native'] + args


# def pytest_sessionfinish(session, exitstatus):
#     breakpoint()
#     pass


def pytest_addoption(parser):
    parser.addoption(
        "--gearbox",
        action="store_true",
        help="Specify the result directory. Use /tmp by default.",
    )

    parser.addoption(
        "--pg",
        action="store_true",
        help="Use pygears pytest plugin",
    )

    parser.addoption(
        "--pg-resdir",
        type=str,
        default=None,
        help="Specify the result directory. Use /tmp by default.",
    )

    parser.addoption(
        "--pg-reuse",
        action="store_true",
        help="Specify the result directory. Use /tmp by default.",
    )
