from enum import IntEnum
import time
import multiprocessing
from pygears.core.hier_node import HierYielderBase
from pygears.conf import inject, Inject
import os
import atexit
from pygears.typing import typeof
from pygears import find
from pygears.core.gear import Gear
from pygears.core.port import HDLConsumer
from pygears.sim import timestep
from .sim_extend import SimExtend

VALUE = set(('0', '1', 'x', 'X', 'z', 'Z'))
INVALID_VALUE = set(('x', 'X', 'z', 'Z'))
VECTOR_VALUE_CHANGE = set(('b', 'B', 'r', 'R'))
VALUE_CHANGE = VALUE | VECTOR_VALUE_CHANGE


class ChannelState(IntEnum):
    Invalid = 0
    NotReady = 1
    Ready = 2
    Done = 3
    Awaiting = 4


import functools


@functools.lru_cache(maxsize=None)
def subtypes(dtype):
    return tuple((t, t.width) for t in dtype)


def split_coded_dtype(t, val):
    for subt, subt_width in t:
        subt_mask = (1 << subt_width) - 1
        yield val & subt_mask
        val >>= subt_width


def split_coded_change(t, val1, val2):
    for subt, subt_width in subtypes(t):
        subt_mask = (1 << subt_width) - 1

        subval1 = val1 & subt_mask
        val1 >>= subt_width

        if val2 is not None:
            subval2 = val2 & subt_mask
            val2 >>= subt_width
        else:
            subval2 = None

        yield subt, subval1, subval2


def create_data_change(t, val, prev_val):
    from pygears.typing import Queue, Array, Tuple
    is_changed = prev_val is None and val is not None or val != prev_val

    if typeof(t, (Queue, Array, Tuple)):
        change = [
            create_data_change(subt, v, prev_v)
            for subt, v, prev_v in split_coded_change(t, val, prev_val)
        ]

        return {'isValueComplex': True, 'isDataChanged': is_changed, 'value': change}
    else:
        if isinstance(val, (int, float)):
            val = int(val)

        return {'isValueComplex': False, 'isDataChanged': is_changed, 'value': val}


class VcdToJson:
    def __init__(self):
        self.json_vcd = {}
        self.diff = {}
        self.state = {}
        self.value = {}

    def create_change(self, timestep, state, state_change, t, val, prev_val):
        elem = {
            'cycle': timestep,
            'state': int(state),
            'isStateChanged': state_change,
        }

        if val is not None:
            elem['data'] = create_data_change(t, val, prev_val)

        return elem

    def after_timestep(self, timestep):
        for p, d in self.diff.items():
            changes = self.json_vcd[p.name]
            new_state = state = self.state[p]
            prev_val = self.value[p]
            new_val = d['d']

            data_change = new_val is not None and (prev_val or self.value[p] != new_val)

            # if data_change:
            #     new_val = p.dtype.decode(d['d'])
            # else:
            #     new_val = None

            if state == ChannelState.Invalid:
                if d['v'] and d['r']:
                    new_state = ChannelState.Ready
                elif d['v']:
                    new_state = ChannelState.NotReady
                elif d['r']:
                    new_state = ChannelState.Awaiting
            elif state == ChannelState.Ready:
                if d['r'] == 0 and d['v'] == 0:
                    new_state = ChannelState.Invalid
                elif d['r'] == 0:
                    new_state = ChannelState.NotReady
                elif d['v'] == 0:
                    new_state = ChannelState.Awaiting
            elif state == ChannelState.NotReady:
                if d['r']:
                    new_state = ChannelState.Ready
            elif state == ChannelState.Awaiting:
                if d['r'] == 0 and d['v']:
                    new_state = ChannelState.NotReady
                elif d['v']:
                    new_state = ChannelState.Ready

            if new_state != state or data_change or timestep == 0:
                cycle_change = self.create_change(timestep,
                                                  new_state,
                                                  state_change=True,
                                                  t=p.dtype,
                                                  val=new_val,
                                                  prev_val=prev_val)

                if cycle_change is not None:
                    changes.append(cycle_change)

            if data_change:
                self.value[p] = new_val

            self.state[p] = new_state

        self.diff.clear()


# def follow(fn, finish_event, sleep_sec=0.1):
#     """ Yield each line from a file as they are written.
#     `sleep_sec` is the time to sleep after empty reads. """
#     line = ''
#     slept = False
#     with open(fn) as f:
#         while True:
#             tmp = f.readline()
#             if tmp:
#                 slept = False
#                 line += tmp
#                 if line.endswith("\n"):
#                     yield line
#                     line = ''
#             else:
#                 if slept:
#                     print('Sleeping consecutively')

#                 slept = True
#                 if finish_event.is_set():
#                     return

#                 time.sleep(sleep_sec)


def follow(fn, finish_event, sleep_sec=0.5):
    import time
    import subprocess
    import select

    f = subprocess.Popen(['tail', '-F', fn], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = select.poll()
    p.register(f.stdout)

    while True:
        if p.poll(sleep_sec):
            yield f.stdout.readline().decode()
        elif finish_event.is_set():
            return
        else:
            # print(f'Sleep')
            time.sleep(sleep_sec)


def vcd_to_json_worker(
    entries,
    wire_map: dict,
    ret: multiprocessing.Queue,
    wid,
):
    vcd_conv = VcdToJson()

    print(f'[{wid}] num: {len(wire_map)}')
    for p, _ in wire_map.values():
        vcd_conv.state[p] = ChannelState.Invalid
        vcd_conv.value[p] = None
        vcd_conv.json_vcd[p.name] = []

    cum_get_delay = 0
    start = time.time()
    t = 0
    while True:
        get_time = time.time()
        res = entries.recv()
        cum_get_delay += time.time() - get_time

        if res is None:
            break

        # print(f'[{wid}] Got {len(res)} entries')
        for identifier_code, value in res:
        # for t, identifier_code, value in iter(entries.get, None):
            # if t is not None:
            #     num_changes = len(vcd_conv.diff)
            #     vcd_conv.after_timestep(t)
            #     # print(
            #     #     f'[{wid}] {t}, diff: {num_changes}, dt: {time.time() - start:.4f}, cum_get_delay: {cum_get_delay:.4f}'
            #     # )
            #     cum_get_delay = 0
            #     start = time.time()
            #     continue

            if identifier_code not in wire_map:
                continue

            port, wire_name = wire_map[identifier_code]
            if port not in vcd_conv.diff:
                vcd_conv.diff[port] = {'r': None, 'v': None, 'd': None}

            if wire_name == 'valid':
                vcd_conv.diff[port]['v'] = value
            elif wire_name == 'ready':
                vcd_conv.diff[port]['r'] = value
            elif wire_name == 'data' and value is not None:
                vcd_conv.diff[port]['d'] = value

        vcd_conv.after_timestep(t)
        t += 1

    ret.send(vcd_conv.json_vcd)


def vcd_to_json(vcd_fn, finish_event, json_vcd, num_workers=2):
    # def vcd_to_json(vcd_fn, json_vcd):
    import os
    import time

    while not os.path.exists(vcd_fn):
        time.sleep(0.1)

    worker_entries = [multiprocessing.Pipe(duplex=False) for _ in range(num_workers)]
    worker_rets = [multiprocessing.Pipe(duplex=False) for _ in range(num_workers)]
    port_maps = [set() for _ in range(num_workers)]
    wire_maps = [{} for _ in range(num_workers)]
    cur_wire_map = 0
    worker_p = []

    # with open(vcd_fn) as f:
    t = -1
    top = find('/')
    hier = top
    worker_data = [[] for _ in range(num_workers)]

    for line in follow(vcd_fn, finish_event):
        # for line in f:
        line = line.strip()
        if line == '':
            continue

        line_head = line[0]

        if line_head == '#':
            next_t = int(line[1:])
            if next_t % 10 != 0:
                continue

            next_t //= 10

            # print(f'Timestep {t}')
            # if t % 100 == 0:
            #     print(f'Timestep {t}')

            if t == -1:
                worker_p = [
                    multiprocessing.Process(target=vcd_to_json_worker,
                                            args=(entries[0], wm, ret[1], i))
                    for i, (entries, wm,
                            ret) in enumerate(zip(worker_entries, wire_maps, worker_rets))
                ]
                for p in worker_p:
                    p.start()

            if t >= 0:
                for i, entries in enumerate(worker_entries):
                    entries[1].send(worker_data[i])
                    worker_data[i].clear()

            t = next_t

        elif line_head in VALUE_CHANGE:
            if line_head in VECTOR_VALUE_CHANGE:
                value, identifier_code = line[1:].split()
            elif line_head in VALUE:
                value = line[0]
                identifier_code = line[1:]

            if value[0] in INVALID_VALUE:
                value = None
            elif value[0] not in ('b', 'B'):
                value = int(value, 2)
            else:
                value = int(value[1:])

            for i, wm in enumerate(wire_maps):
                if identifier_code in wm:
                    worker_data[i].append((identifier_code, value))

            # start = time.time()
            # for entries, wm in zip(worker_entries, wire_maps):
            #     if identifier_code in wm:
            #         entries[1].send((None, identifier_code, value))
            #         break
            # send_cum_t += time.time() - start

        elif '$enddefinitions' in line:
            pass
        elif '$scope' in line:
            segs = line.split()
            # Name of the TOP is ' '
            if len(segs) == 3:
                hier = top
                continue

            scope_name = segs[2]

            child = find(f'{hier.name}.{scope_name}')

            if child is None:
                child = hier[scope_name]

            if child is None:
                raise Exception(f'Cannot find gear for scope: {line}')

            hier = child

        elif '$upscope' in line:
            if isinstance(hier, Gear):
                if hier is not top:
                    hier = hier.parent
            else:
                hier = hier.gear
        elif '$var' in line:
            if hier is top:
                continue

            ls = line.split()
            identifier_code = ls[3]
            name = ''.join(ls[4:-1])

            for i, pm in enumerate(port_maps):
                if hier.name in pm:
                    wire_maps[i][identifier_code] = (hier, name)
                    break
            else:
                wire_maps[cur_wire_map][identifier_code] = (hier, name)
                port_maps[cur_wire_map].add(hier.name)
                cur_wire_map = (cur_wire_map + 1) % num_workers

        elif '$timescale' in line:
            continue

    print(f'Time: {time.time()}')
    for entries in worker_entries:
        entries[1].send(None)

    print(f'Time start rets: {time.time()}')
    ret_combine = {}
    for ret in worker_rets:
        ret_combine.update(ret[0].recv())

    print(f'Time got rets: {time.time()}')

    for p in worker_p:
        p.join()

    print(f'Time put outputs: {time.time()}')
    json_vcd.put(ret_combine)
    # return vcd_conv.json_vcd


def dtype_tree(dtype):
    from pygears.typing import Queue, Array, Tuple
    if issubclass(dtype, Array):
        return {'name': repr(dtype), 'subtypes': [dtype_tree(t) for t in dtype]}
    elif issubclass(dtype, (Queue, Array, Tuple)):
        return {
            'name': repr(dtype),
            'subtypes': [dtype_tree(t) for t in dtype],
            'keys': dtype.fields
        }
    else:
        return {'name': repr(dtype)}


def dump_json_graph(top):

    nodes = {}
    ports = {}
    connections = {}

    class NodeYielder(HierYielderBase):
        def Gear(self, node):
            yield node

    for node in NodeYielder().visit(find(top)):
        in_ports = []
        for p in node.in_ports:
            ports[p.name] = {
                'basename': p.basename,
                'name': p.name,
                'dtype': repr(p.dtype),
                'index': p.index
            }
            in_ports.append(p.name)

        out_ports = []
        for p in node.out_ports:
            ports[p.name] = {
                'basename': p.basename,
                'name': p.name,
                'dtype': repr(p.dtype),
                'index': p.index
            }
            out_ports.append(p.name)

        node_json = {
            'basename': node.basename,
            'name': node.name,
            'definition': 'None' if node.definition is None else
            f'{node.definition.func.__module__}.{node.definition.func.__name__}',
            'in_ports': in_ports,
            'out_ports': out_ports
        }

        nodes[node.name] = node_json

    for node in NodeYielder().visit(find(top)):
        nodes[node.name]['child'] = []
        for c in node.child:
            nodes[node.name]['child'].append(c.name)

    for node in NodeYielder().visit(find(top)):
        for p in node.in_ports + node.out_ports:
            if p.consumer is None:
                continue

            i = p.consumer
            connections[i.name] = {
                'producer': i.producer.name,
                'dtype': repr(p.dtype),
                'dtype_tree': dtype_tree(p.dtype),
                'name': i.name,
                'consumers': [pc.name for pc in i.consumers if not isinstance(pc, HDLConsumer)]
            }

            ports[i.producer.name]['consumer'] = i.name
            for p in i.consumers:
                if isinstance(p, HDLConsumer):
                    continue

                ports[p.name]['producer'] = i.name

        # for i in node.local_intfs:
        #     if i.name == '.depthwise':
        #         breakpoint()

        #     connections[i.producer.name] = {
        #         'producer': i.producer.name,
        #         'dtype': repr(p.dtype),
        #         'dtype_tree': dtype_tree(p.dtype),
        #         'name': i.name,
        #         'consumers': [p.name for p in i.consumers]
        #     }
        #     ports[i.producer.name]['consumer'] = i.name
        #     for p in i.consumers:
        #         ports[p.name]['producer'] = i.name

    return {'gears': nodes, 'ports': ports, 'connections': connections}

    # import json
    # # s = json.dumps({'gears': nodes, 'ports': ports, 'connections': connections})

    # with open(fn, 'w') as f:
    #     f.write(json.dumps(graph, indent=4, sort_keys=True))


class WebSim(SimExtend):
    @inject
    def __init__(self, trace_fn='pygears.json', outdir=Inject('results-dir')):
        super().__init__()
        self.outdir = outdir
        self.trace_fn = os.path.abspath(os.path.join(self.outdir, trace_fn))
        # atexit.register(self.finish)

        self.vcd_fn = os.path.abspath(os.path.join(self.outdir, 'pygears.vcd'))
        self.finished = False

        self.json_vcd = {}
        manager = multiprocessing.Manager()
        self.json_vcd = manager.dict()

        self.q = multiprocessing.Queue()
        self.finish_event = multiprocessing.Event()
        self.p = multiprocessing.Process(target=vcd_to_json,
                                         args=(self.vcd_fn, self.finish_event, self.q))
        self.p.start()

    def sim_vcd_to_json(self):
        import time
        start = time.time()
        graph = dump_json_graph('/')
        print(f'Graph dump in {time.time() - start:.2f}')

        start = time.time()

        # from pycallgraph import PyCallGraph
        # from pycallgraph.output import GraphvizOutput

        # with PyCallGraph(output=GraphvizOutput()):
        # json_vcd = vcd_to_json(self.vcd_fn, self.json_vcd)

        # self.p = multiprocessing.Process(target=vcd_to_json,
        #                                  args=(self.vcd_fn, q))
        # self.p.start()

        self.finish_event.set()
        self.json_vcd = self.q.get()
        self.p.join()

        changes = []
        for p_name in self.json_vcd:
            p = find(p_name)
            changes.append({'channelName': p.producer.name, 'changes': self.json_vcd[p_name]})

        print(f'Change dump aditional {time.time() - start:.2f}')

        return {
            'graphInfo': graph,
            'simulationChanges': {
                'startCycle': 0,
                'endCycle': timestep(),
                'channelChanges': changes
            }
        }

    def finish(self):
        if not self.finished:
            json_out = self.sim_vcd_to_json()
            import json
            json.dump(json_out, open(self.trace_fn, 'w'))
            self.finished = True

    def after_cleanup(self, sim):
        self.finish()
