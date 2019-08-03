import runpy
import os
from pygears import config, find, clear
from pygears.sim.extens.wavejson import WaveJSON
from pygears.sim import sim

examples_dir = '/tools/home/pygears/docs/manual/gears/examples'


def get_example_gear(example):
    for c in find('/').child:
        if not c.name.startswith(example.split('_')[0]):
            continue

        return c

    for c in find('/').child:
        if c.definition.func.__module__ == 'pygears.lib.verif':
            continue

        if (c.basename == 'delay_gen'):
            continue

        if (c.basename == 'ccat') and (not example.startswith('ccat')):
            continue

        return c


def run_file(path):
    print(f'Running example {path}')
    example = os.path.splitext(os.path.basename(path))[0]
    cfg_fn = os.path.splitext(path)[0] + '_cfg.py'

    clear()
    runpy.run_path(path)

    if os.path.exists(cfg_fn):
        runpy.run_path(cfg_fn)
    else:
        gear = get_example_gear(example).basename

        for inp in find(f'/{gear}').in_ports:
            config['hdl/debug_intfs'].append(inp.name)

        for outp in find(f'/{gear}').out_ports:
            config['hdl/debug_intfs'].append(outp.name)

    # config['sim/artifacts_dir'] = '/tools/home/tmp'
    config['wavejson/trace_fn'] = os.path.join(examples_dir, f'{example}.json')
    config['sim/extens'].append(WaveJSON)
    # config['trace/level'] = 0

    sim()


def run_example(example):
    path = os.path.join(examples_dir, f'{example}.py')
    run_file(path)


def run_all():
    for f in os.listdir(examples_dir):
        path = os.path.join(examples_dir, f)
        if (not os.path.isfile(path) or os.path.splitext(f)[-1] != '.py'):
            continue

        run_file(path)


example = 'fmap_union'
run_example(example)
# run_all()
