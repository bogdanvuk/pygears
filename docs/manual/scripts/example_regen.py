import runpy
import os
from pygears import config, find, clear
from pygears.sim.extens.wavejson import WaveJSON
from pygears.sim import sim

examples_dir = '/tools/home/pygears/docs/manual/gears/examples'


def run_file(path):
    print(f'Running example {path}')
    example = os.path.splitext(os.path.basename(path))[0]

    clear()
    runpy.run_path(path)

    for c in find('/').child:
        if c.definition.func.__module__ == 'pygears.lib.verif':
            continue

        gear = c.basename

        for inp in find(f'/{gear}').in_ports:
            config['hdl/debug_intfs'].append(inp.name)

        for outp in find(f'/{gear}').out_ports:
            config['hdl/debug_intfs'].append(outp.name)

        break

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


example = 'reduce_sum'
run_example(example)
# run_all()
