try:
    import matplotlib
    from matplotlib.ticker import FuncFormatter
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
except ImportError:
    pass

import queue
from pygears.typing import Array, typeof
from pygears import gear, module, GearDone, config, registry
from pygears.sim import timestep, clk

import multiprocessing

suffix = ["G", "M", "k", "", "m", "u", "n", "p"]
decades = [1e9, 1e6, 1e3, 1e0, 1e-3, 1e-6, 1e-9, 1e-12]


def plot_process(qin, clk_freq, chnum, title=None, scale=None, method=None):

    fig, ax = plt.subplots()

    if title:
        plt.title(title)

    if method is None:
        method = ['plot'] * chnum

    line = [getattr(ax, method[i])([], [], lw=2)[0] for i in range(chnum)]

    ax.grid()
    ax.set_xlim(0, 1 / clk_freq)

    tmp = clk_freq
    positions = 0
    while tmp > 1:
        positions += 1
        tmp /= 10

    def t_fmt(t, posp):
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

                str_val = str_val[:-cutoff]

                return f'{str_val} {suffix[i]}'

        return t

    ax.xaxis.set_major_formatter(FuncFormatter(t_fmt))

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

                ch, t, y = res

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

    _ = CustFuncAnimation(fig,
                          run,
                          data_gen,
                          blit=False,
                          interval=100,
                          repeat=False)

    plt.show()


@gear(enablement=b'"matplotlib" in globals()')
async def scope(*xs, clk_freq=None, title=None, scale=None, method=None):
    if clk_freq is None:
        clk_freq = config['sim/clk_freq']

    qin = multiprocessing.Queue(maxsize=10000)

    if title is None:
        title = module().name

    parallel_steps = max(
        len(x.dtype) if typeof(x.dtype, Array) else 1 for x in xs)

    _proc = multiprocessing.context.Process(
        target=plot_process,
        args=(qin, clk_freq * parallel_steps, len(xs), title, scale, method))
    _proc.start()

    def cleanup(sim):
        if not registry('sim/exception'):
            _proc.join()
        else:
            _proc.terminate()

    registry('sim/simulator').events['after_cleanup'].append(cleanup)

    try:
        while True:
            for ch, x in enumerate(xs):
                if x.done:
                    raise GearDone

                if x.empty():
                    continue

                async with x as x_data:
                    if not isinstance(x_data, Array):
                        x_data = [x_data]

                    for i, v in enumerate(x_data):
                        qin.put((ch, (timestep() + i / len(x_data)) / clk_freq,
                                 float(v)))

            await clk()

    except GearDone:
        qin.put(None)
        raise GearDone
