try:
    import matplotlib
    from matplotlib.ticker import FuncFormatter
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
except ImportError:
    pass

import os
import queue
import pickle
from functools import partial
from pygears.typing import Array, typeof, Queue
from pygears import gear, module, GearDone, reg
from pygears.sim import timestep, clk

import multiprocessing

suffix = ["G", "M", "k", "", "m", "u", "n", "p"]
decades = [1e9, 1e6, 1e3, 1e0, 1e-3, 1e-6, 1e-9, 1e-12]

colors = {
    'line': "#355c7d",
    'handshake': "#c06c84",
    'eot': "#f67280",
}


def t_fmt(t, posp, positions):
    if t == 0:
        return str(0)

    for i, d in enumerate(decades):
        if abs(t) >= d:
            val = int(round((t / float(d)) * (10**positions)))
            str_val = str(val)
            str_val = str_val[:-positions] + '.' + str_val[-positions:]

            for cutoff in range(0, positions + 2):
                if str_val[-(cutoff + 1)] in ['0', '.']:
                    continue

                break

            if cutoff:
                str_val = str_val[:-cutoff]

            return f'{str_val} {suffix[i]}'

    return t


def create_plot(title, method, clk_freq):
    fig, ax = plt.subplots()

    if title:
        plt.title(title)

    line = []
    for m in method:
        if isinstance(m, str):
            kwds = {'linewidth': 2, 'color': colors['line']}
            if m == 'step':
                kwds['where'] = 'post'

            line.append(getattr(ax, m)([], [], **kwds)[0])
        else:
            line.append(m(ax, x=[], y=[]))

    ax.grid()
    ax.set_xlim(0, 1 / clk_freq)

    tmp = clk_freq
    positions = 0
    while tmp > 1:
        positions += 1
        tmp /= 10

    ffmt = FuncFormatter(partial(t_fmt, positions=positions))
    fig.ffmt = ffmt
    ax.xaxis.set_major_formatter(ffmt)

    return fig, ax, line


def plot_process(method, qin, clk_freq, title=None, scale=None):

    fig, ax, line = create_plot(title, method, clk_freq)

    chnum = len(method)

    xdata = [[] for _ in range(chnum)]
    ydata = [[] for _ in range(chnum)]

    yrng = [0, 0]
    done = []

    class CustFuncAnimation(animation.FuncAnimation):
        def _init_draw(self):
            try:
                super()._init_draw()
            except StopIteration:
                super()._draw_frame(tuple(yrng))

    def data_gen():
        while True:
            while True:
                if done:
                    return

                try:
                    res = qin.get(block=True, timeout=1.0)
                except queue.Empty:
                    yield tuple(yrng)
                    continue

                if res is None:
                    done.append(True)
                    break

                ch, t, y, _ = res

                if scale:
                    y *= scale[ch]

                xdata[ch].append(t)
                ydata[ch].append(y)

                if y > yrng[1]:
                    yrng[1] = y

                if y < yrng[0]:
                    yrng[0] = y

                if qin.empty():
                    break

            yield tuple(yrng)

            if res is None:
                break

    def run(yrng):
        t = max(xdata[i][-1] if xdata[i] else 0 for i in range(chnum))
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()

        redraw = bool(done)
        if t >= xmax:
            ax.set_xlim(xmin, 1.5 * t)
            redraw = True

        if (ymax < yrng[1] * 1.1) or (ymin > yrng[0]):
            ax.set_ylim(yrng[0], yrng[1] * 1.1)
            redraw = True

        for i in range(chnum):
            line[i].set_data(xdata[i], ydata[i])

        if redraw:
            ax.figure.canvas.draw()

        return

    _ = CustFuncAnimation(fig, run, data_gen, blit=False, interval=100, repeat=False)

    plt.show()


def plot_live(method, clk_freq, title, scale, transaction):
    qin = multiprocessing.Queue(maxsize=10000)

    _proc = multiprocessing.context.Process(
        target=plot_process, args=(method, qin, clk_freq, title, scale))
    _proc.start()

    def cleanup(sim):
        if not reg['sim/exception']:
            _proc.join()
        else:
            _proc.terminate()

    reg['sim/simulator'].events['after_cleanup'].append(cleanup)

    try:
        while True:
            qin.put((yield None))
    except GeneratorExit:
        qin.put(None)


def plot_dump(files, method, clk_freq, title, scale, transaction):
    fig, ax, line = create_plot(title, method, clk_freq)

    chnum = len(method)

    xdata = [[] for _ in range(chnum)]
    ydata = [[] for _ in range(chnum)]
    eots = [[] for _ in range(chnum)]

    from matplotlib import patches
    try:
        while True:
            ch, t, val, eot = yield None
            if eot:
                eots[ch].append(t)

            xdata[ch].append(t)
            ydata[ch].append(val)
    except GeneratorExit:
        pass

    ax.set_autoscale_on(True)
    for i in range(chnum):
        ymax = max(ydata[i])
        ymin = min(ydata[i])

        def handshake(x1, x2, color, alpha):
            rect = patches.Rectangle(
                (x1, ymin), x2 - x1, ymax - ymin, color=color, fill=True, alpha=alpha)
            ax.add_patch(rect)

        if transaction:
            next_t = None
            rect_start_t = None

            for t in xdata[i]:
                if rect_start_t is None:
                    rect_start_t = t

                if (next_t is not None and (t - next_t) > 1 / (2 * clk_freq)):
                    handshake(rect_start_t, next_t, colors['handshake'], 0.13)
                    rect_start_t = t

                next_t = t + 1 / clk_freq

            if (next_t is not None and (next_t - rect_start_t) > 1 / (2 * clk_freq)):
                handshake(rect_start_t, next_t, colors['handshake'], 0.13)

            for t in eots[i]:
                handshake(t, t + 1 / clk_freq, colors['eot'], 0.5)

        ydata[i].append(ydata[i][-1])
        xdata[i].append(xdata[i][-1] + 1 / clk_freq)
        line[i].set_data(xdata[i], ydata[i])

    ax.relim()
    ax.autoscale_view(True, True, True)
    # plt.axhline(xmin=0.1, xmax=0.2, linewidth=8, color='#d62728')
    # plt.hlines(y=0.5, xmin=0.0, xmax=0.02, linewidth=8, color='#d62728', solid_capstyle='round')
    # plt.fill_between([0, 0.02], [10, 10])

    # Add the patch to the Axes
    # plt.bar([0, 0.02], [0, 0], linewidth=8, color='#d62728', solid_capstyle='round', alpha=0.5)
    # plt.axvspan(0, 0.02, facecolor='#3cb03c', alpha=0.3)
    # plt.axvspan(0.02, 0.04, facecolor='#0c600c', alpha=0.35)
    # ax.axhline(linewidth=8, color='#d62728')
    fig.canvas.draw()

    for f in files.split(','):
        if f == 'show':
            continue

        os.makedirs(os.path.dirname(f), exist_ok=True)
        if os.path.splitext(f)[1] == '.pkl':
            with open(f, 'wb') as fid:
                pickle.dump(fig, fid)
        else:
            fig.savefig(f)

    if 'show' in files.split(','):
        plt.show()

    plt.close(fig)


@gear(enablement=b'"matplotlib" in globals()')
async def scope(
    *xs,
    clk_freq=None,
    title=None,
    scale=None,
    method=None,
    live=None,
    dump=None,
    transaction=False):

    if clk_freq is None:
        clk_freq = reg['sim/clk_freq']

    if method is None:
        method = ['plot'] * len(xs)

    if len(method) != len(xs):
        raise Exception(
            f'Number of plotting methods ({method}) needs to match the number of inputs ({len(xs)})')

    if title is None:
        title = module().name

    parallel_steps = max(len(x.dtype) if typeof(x.dtype, Array) else 1 for x in xs)

    backends = []

    kwds = {
        'method': method,
        'clk_freq': clk_freq * parallel_steps,
        'title': title,
        'scale': scale,
        'transaction': transaction
    }

    if live or (live is None and dump is None):
        backends.append(plot_live(**kwds))

    if dump:
        backends.append(plot_dump(dump, **kwds))

    for b in backends:
        b.send(None)

    try:
        while True:
            for ch, x in enumerate(xs):
                if x.done:
                    raise GearDone

                if x.empty():
                    continue

                async with x as x_data:
                    if isinstance(x_data, Queue):
                        x_data, eot = x_data
                    else:
                        eot = 0

                    if not isinstance(x_data, Array):
                        x_data = [x_data]

                    for i, v in enumerate(x_data):
                        point = (
                            ch, (timestep() + i / len(x_data)) / clk_freq, float(v), int(eot))

                        for b in backends:
                            b.send(point)

            await clk()

    except GearDone:
        for b in backends:
            b.close()
        raise GearDone
